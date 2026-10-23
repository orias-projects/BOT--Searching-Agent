"""
Bootstrap + pipelines: DocumentPipeline (OOP) load config, services, indexes;
expose process_pdf_pipeline, search_pipeline, summarize_text.
Chạy từ project root; paths trong config là relative to root.
"""
from typing import Optional
import sys
from pathlib import Path as PathlibPath

# Add project root (5 levels up: pipelines → usecases → core → backends → src → root) to path
_project_root = PathlibPath(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import faiss
import fitz
from sentence_transformers import CrossEncoder

from configs.configs import AppConfig, ConfigValues
from src.backends.infra.model_loader import ModelLoader
from src.scripts import commonMyUtils as MU
from src.scripts import commonTextProcess as TP
from src.scripts.dataProcessing import pdfQualityCheck as QualityCheck
from src.scripts.dataProcessing import pdfExtractData as ExtractData
from src.scripts.dataProcessing import pdfMergeData as MergeData
from src.scripts.jsonProcessing import jsonChunkUnder as ChunkUnder
from src.scripts.jsonProcessing import jsonGetStructures as GetStructures
from src.scripts.jsonProcessing import jsonChunkMaster as ChunkMaster
from src.scripts.jsonProcessing import jsonSchemaExt as SchemaExt
from src.scripts.legacyFaiss import faissEmbedding as F_Embedding
from src.scripts.legacyFaiss import faissSearching as F_Searching
from src.scripts.legacyFaiss import faissChunkMapping as chunkMapper
from src.scripts.llmServices import summarizerRunner as SummaryRun
from src.backends.core.services.pgVectorStore import PGVectorStore
from src.scripts.legacyFaiss.sqliteVectorStore import SQLiteVectorStore


def _load_hardcodes(file_path: str, wanted=None) -> dict:
    data = MU.readJson(file_path)
    if not isinstance(data, dict) or "items" not in data:
        return {}
    result = {}
    for item in data["items"]:
        key = item.get("key")
        if key and ((not wanted) or (key in wanted)):
            result[key] = item.get("values", [])
    return result


def _read_index_data(seg_path: str, faiss_path: str, map_path: str, map_data_path: str, map_chunk_path: str) -> dict:
    try:
        segment_dict = MU.readJson(seg_path)
        faiss_index = faiss.read_index(faiss_path)
        mapping = MU.readJson(map_path)
        map_data = MU.readJson(map_data_path)
        map_chunk = MU.readJson(map_chunk_path)
        return {
            "segmentDict": segment_dict,
            "faissIndex": faiss_index,
            "mapping": mapping,
            "mapData": map_data,
            "mapChunk": map_chunk,
        }
    except Exception:
        return {
            "segmentDict": None,
            "faissIndex": None,
            "mapping": None,
            "mapData": None,
            "mapChunk": None,
        }


class DocumentPipeline:
    """
    Pipeline xử lý tài liệu RAG: trích xuất PDF, tóm tắt, tìm kiếm, phân loại.
    Tất cả config và services được inject qua constructor; không dùng biến global.
    """

    INFILENAME = "HNMU"
    JSON_KEY = "paragraphs"
    JSON_FIELD = "Text"
    DROP_FIELDS = ["Index"]

    def __init__(self, config: Optional[AppConfig] = None, pdfname: Optional[str] = None) -> None:
        self._config = config or ConfigValues(
            pdfname=pdfname or self.INFILENAME,
        )
        self._models_folder = self._config.get("modelsFolder", "models/resource")
        self._except_path = self._config["exceptPath"]
        self._marker_path = self._config["markerPath"]
        self._status_path = self._config["statusPath"]
        self._raw_data_path = self._config["rawDataPath"]
        self._segment_path = self._config["segmentPath"]
        self._faiss_path = self._config["faissPath"]
        self._mapping_path = self._config["mappingPath"]
        self._map_data_path = self._config["mapDataPath"]
        self._map_chunk_path = self._config["mapChunkPath"]
        self._use_pg_vector = bool(self._config.get("usePgVector", False))
        self._database_url = (self._config.get("databaseUrl") or "").strip()
        self._use_sqlite_vector = bool(self._config.get("useSqliteVector", False))
        self._sqlite_db_path = (self._config.get("sqliteDbPath") or "").strip()
        self._embedding_dim = int(self._config.get("embeddingDim", 768))

        embedd_model = self._config["EMBEDD_MODEL"]
        chunks_model = self._config["CHUNKS_MODEL"]
        sumary_model = self._config["SUMARY_MODEL"]
        rerank_model = self._config["RERANK_MODEL"]
        embedd_cached = f"{self._models_folder}/Sentence_Transformer/{embedd_model}"
        chunks_cached = f"{self._models_folder}/Sentence_Transformer/{chunks_model}"
        sumary_cached = f"{self._models_folder}/Summarizer/{sumary_model}"

        except_data = _load_hardcodes(self._except_path, wanted=["common_words", "proper_names", "abbreviations"])
        marker_data = _load_hardcodes(self._marker_path, wanted=["keywords", "markers"])
        status_data = _load_hardcodes(self._status_path, wanted=["brackets", "sentence_ends"])

        loader = ModelLoader()
        self._indexer, self._embedd_device = loader.loadEncoder(embedd_model, embedd_cached)
        _chunker, _chunks_device = loader.loadEncoder(chunks_model, chunks_cached)
        self._tokenizer, self._summarizer, self._summary_device = loader.loadSummarizer(sumary_model, sumary_cached)

        self._checker = QualityCheck.PDFQualityChecker()
        self._data_extractor = ExtractData.B1Extractor(
            except_data, marker_data, status_data, properNameMinCount=10
        )
        self._merger = MergeData.ParagraphMerger()
        self._struct_analyzer = GetStructures.StructureAnalyzer(verbose=True)
        self._chunk_builder = ChunkMaster.ChunkBuilder()
        self._schema_ext = SchemaExt.JSONSchemaExtractor(listPolicy="first", verbose=True)
        self._faiss_indexer = F_Embedding.DirectFaissIndexer(
            indexer=self._indexer,
            device=str(self._embedd_device),
            batch_size=32,
            show_progress=True,
            flatten_mode="split",
            join_sep="\n",
            allowed_schema_types=("string", "array", "dict"),
            max_chars_per_text=2000,
            normalize=True,
            verbose=False,
        )
        self._chunk_under = ChunkUnder.ChunkUndertheseaBuilder(
            embedder=self._indexer,
            device=self._embedd_device,
            minWords=256,
            maxWords=768,
            simThreshold=0.7,
            keySentRatio=0.4,
        )
        self._summary_engine = SummaryRun.RecursiveSummarizer(
            tokenizer=self._tokenizer,
            summarizer=self._summarizer,
            sumDevice=self._summary_device,
            chunkBuilder=self._chunk_under,
            maxLength=200,
            minLength=100,
            maxDepth=4,
        )
        self._reranker = CrossEncoder(rerank_model, device=str(self._embedd_device))
        self._search_engine = F_Searching.SemanticSearchEngine(
            indexer=self._indexer,
            reranker=self._reranker,
            device=str(self._embedd_device),
            normalize=True,
            topK=20,
            rerankK=10,
            rerankBatchSize=16,
        )

        self._segment_dict = None
        self._faiss_index = None
        self._mapping = None
        self._map_data = None
        self._map_chunk = None
        self._pg_main_store: Optional[PGVectorStore] = None
        self._sqlite_main_store: Optional[SQLiteVectorStore] = None

        if self._use_sqlite_vector and self._sqlite_db_path:
            self._load_indexes_sqlite()
        elif self._use_pg_vector and self._database_url:
            self._load_indexes_pg()
        else:
            self._load_indexes_faiss()

    def _load_indexes_faiss(self) -> None:
        print("Server is starting, loading main search index (FAISS)...")
        try:
            main_data = _read_index_data(
                self._segment_path,
                self._faiss_path,
                self._mapping_path,
                self._map_data_path,
                self._map_chunk_path,
            )
            self._segment_dict = main_data["segmentDict"]
            self._faiss_index = main_data["faissIndex"]
            self._mapping = main_data["mapping"]
            self._map_data = main_data["mapData"]
            self._map_chunk = main_data["mapChunk"]
            if self._faiss_index is not None:
                print(f"[SUCCESS] Main search index '{self.INFILENAME}' loaded (FAISS).")
            else:
                print(f"[FAILED] Could not load main search index from {self._faiss_path}.")
        except Exception as e:
            print(f"[CRITICAL] Failed to load main search index: {e}")
            self._faiss_index = None



    def _load_indexes_pg(self) -> None:
        print("Server is starting, loading main search index (PostgreSQL)...")
        try:
            self._segment_dict = MU.readJson(self._segment_path) if self._segment_path else None
            self._pg_main_store = PGVectorStore(
                self._database_url,
                index_name=PGVectorStore.INDEX_MAIN,
                dimension=self._embedding_dim,
            )
            self._pg_main_store.connect()
            self._pg_main_store.ensure_extension_and_table()
            n_main = self._pg_main_store.count()
            if n_main > 0:
                print(f"[SUCCESS] Main search index loaded (PostgreSQL, {n_main} vectors).")
            else:
                print("[WARN] Main PostgreSQL index empty. Chạy script build index PG trước khi search.")
        except Exception as e:
            print(f"[CRITICAL] Failed to load main PostgreSQL index: {e}")
            self._pg_main_store = None



    def _load_indexes_sqlite(self) -> None:
        print("Server is starting, loading main search index (SQLite)...")
        try:
            self._segment_dict = MU.readJson(self._segment_path) if self._segment_path else None
            self._sqlite_main_store = SQLiteVectorStore(
                self._sqlite_db_path,
                index_name=SQLiteVectorStore.INDEX_MAIN,
                dimension=self._embedding_dim,
            )
            self._sqlite_main_store.connect()
            self._sqlite_main_store.ensure_extension_and_table()
            n_main = self._sqlite_main_store.count()
            if n_main > 0:
                print(f"[SUCCESS] Main search index loaded (SQLite, {n_main} vectors).")
            else:
                print("[WARN] Main SQLite index empty. Chạy script build index SQLite trước khi search.")
        except Exception as e:
            print(f"[CRITICAL] Failed to load main SQLite index: {e}")
        
        # Categories service removed - system now only answers questions
            self._sqlite_main_store = None

        print(f"Loading '{self.SERVICE_NAME}' index (SQLite)...")
        try:
            self._service_segment_dict = MU.readJson(self._service_segment_path) if self._service_segment_path else None
            self._sqlite_service_store = SQLiteVectorStore(
                self._sqlite_db_path,
                index_name=SQLiteVectorStore.INDEX_SERVICE,
                dimension=self._embedding_dim,
            )
            self._sqlite_service_store.connect()
            self._sqlite_service_store.ensure_extension_and_table()
            n_svc = self._sqlite_service_store.count()
            if n_svc > 0:
                print(f"[SUCCESS] '{self.SERVICE_NAME}' index loaded (SQLite, {n_svc} vectors).")
            else:
                print(f"[WARN] '{self.SERVICE_NAME}' SQLite index empty.")
        except Exception as e:
            print(f"[CRITICAL] Failed to load '{self.SERVICE_NAME}' SQLite index: {e}")
            self._sqlite_service_store = None

    def _extract_run(self, pdf_doc) -> dict:
        extracted = self._data_extractor.extract(pdf_doc)
        return self._merger.merge(extracted)

    def _pre_read_pdf(self, pdf_path=None, pdf_bytes=None) -> dict | None:
        if pdf_bytes is not None:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        elif pdf_path is not None:
            pdf_doc = fitz.open(pdf_path)
        else:
            return None
        is_good, _ = self._checker.evaluate(pdf_doc)
        if not is_good:
            pdf_doc.close()
            return None
        raw_data = self._extract_run(pdf_doc)
        if self._raw_data_path:
            MU.writeJson(raw_data, self._raw_data_path, indent=1)
        pdf_doc.close()
        return raw_data

    def _merge_by_text(self, raw_data_dict: dict) -> dict:
        return TP.mergeTxt(raw_data_dict, self.JSON_KEY, self.JSON_FIELD)

    def _summary_run(self, merged_text: dict) -> dict:
        return self._summary_engine.summarize(merged_text, minInput=256, maxInput=1024)

    def _run_search(
        self,
        query: str,
        faiss_index=None,
        mapping=None,
        map_data=None,
        map_chunk=None,
        pg_store: Optional[PGVectorStore] = None,
        sqlite_store: Optional[SQLiteVectorStore] = None,
        top_k: int = 20,
    ):
        if self._use_sqlite_vector and sqlite_store is not None:
            return self._search_engine.search_with_vector_store(
                query=query, vector_store=sqlite_store, topK=top_k
            )
        if self._use_pg_vector and pg_store is not None:
            return self._search_engine.search_with_vector_store(
                query=query, vector_store=pg_store, topK=top_k
            )
        return self._search_engine.search(
            query=query,
            faissIndex=faiss_index,
            mapping=mapping,
            mapData=map_data,
            mapChunk=map_chunk,
            topK=top_k,
        )

    def _run_rerank(self, query: str, results, top_k: int = 10):
        return self._search_engine.rerank(query=query, results=results, topK=top_k)

    def _chunk_map(self, reranked, segment_dict, drop_fields, fields, n_chunks):
        return chunkMapper.processChunksPipeline(
            reranked=reranked,
            segmentDict=segment_dict,
            dropFields=drop_fields,
            fields=fields,
            nChunks=n_chunks,
        )

    def summarize_pipeline(self, raw_data_dict: dict) -> str:
        if not raw_data_dict:
            return ""
        merged = self._merge_by_text(raw_data_dict)
        summarized = self._summary_run(merged)
        return summarized.get("summaryText", "")

    def process_pdf_pipeline(self, pdf_bytes: bytes) -> dict:
        raw_data = self._pre_read_pdf(pdfPath=None, pdfBytes=pdf_bytes)
        if raw_data is None:
            return {
                "checkstatus": "failed",
                "summary": "",
                "category": "PDF không hợp lệ hoặc không thể trích xuất",
            }
        summary_text = self.summarize_pipeline(raw_data)
        if True:
            best_article = "Không thể phân loại (chưa tải index)"
        else:
            search_res = self._run_search(
                summary_text,
                faiss_index=self._service_faiss_index,
                mapping=self._service_mapping,
                map_data=self._service_map_data,
                map_chunk=self._service_map_chunk,
                pg_store=self._pg_service_store,
                sqlite_store=self._sqlite_service_store,
                top_k=20,
            )
            reranked = self._run_rerank(summary_text, search_res)
            best_category = self._chunk_map(
                reranked,
                self._service_segment_dict,
                self.DROP_FIELDS,
                fields=["Article"],
                n_chunks=1,
            )
            best_articles = [
                item["fields"].get("Article")
                for item in best_category.get("extractedFields", [])
            ]
            best_article = best_articles[0] if best_articles else "Không xác định"
        return {
            "checkstatus": "ok",
            "summary": summary_text,
            "category": best_article,
        }

    def search_pipeline(self, query_text: str, k: int = 10) -> list:
        main_ready = (
            self._faiss_index is not None
            or (self._pg_main_store is not None and self._pg_main_store.count() > 0)
            or (self._sqlite_main_store is not None and self._sqlite_main_store.count() > 0)
        )
        if not main_ready:
            return []
        search_res = self._run_search(
            query_text,
            faiss_index=self._faiss_index,
            mapping=self._mapping,
            map_data=self._map_data,
            map_chunk=self._map_chunk,
            pg_store=self._pg_main_store,
            sqlite_store=self._sqlite_main_store,
            top_k=20,
        )
        reranked = self._run_rerank(query_text, search_res)
        chunk_return = self._chunk_map(
            reranked,
            self._segment_dict,
            self.DROP_FIELDS,
            fields=None,
            n_chunks=k,
        )
        return chunk_return.get("extractedFields", [])

    def summarize_text(self, text: str) -> dict:
        if not (text or str(text).strip()):
            return {"summaryText": ""}
        return self._summary_engine.summarize(str(text).strip(), minInput=0, maxInput=1024)

    @property
    def main_index_loaded(self) -> bool:
        if self._use_sqlite_vector and self._sqlite_main_store:
            return self._sqlite_main_store.count() > 0
        if self._use_pg_vector and self._pg_main_store:
            return self._pg_main_store.count() > 0
        return self._faiss_index is not None




# Singleton và API cho app
_document_pipeline: Optional[DocumentPipeline] = None


def get_document_pipeline() -> DocumentPipeline:
    global _document_pipeline
    if _document_pipeline is None:
        _document_pipeline = DocumentPipeline()
    return _document_pipeline


def processPdfPipeline(pdf_bytes: bytes) -> dict:
    return get_document_pipeline().process_pdf_pipeline(pdf_bytes)


def searchPipeline(query_text: str, k: int = 10) -> list:
    return get_document_pipeline().search_pipeline(query_text, k=k)


def summarizeText(text: str) -> dict:
    return get_document_pipeline().summarize_text(text)
