"""
Extract JSON schema from segment dict (types per key).
"""
from typing import Any, Dict, List


class JSONSchemaExtractor:
    def __init__(self, listPolicy: str = "first", verbose: bool = True) -> None:
        assert listPolicy in ("first", "union")
        self.listPolicy = listPolicy
        self.verbose = verbose
        self._processedFields: set = set()
        self._fullSchema: Dict[str, str] = {}

    @staticmethod
    def getStandardType(value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        if value is None:
            return "null"
        return "unknown"

    def _mergeType(self, key: str, newType: str, itemIndex: int) -> None:
        if key not in self._fullSchema:
            self._fullSchema[key] = newType
            self._processedFields.add(key)
            return
        oldType = self._fullSchema[key]
        if oldType == newType:
            return
        if newType == "null":
            return
        if oldType == "null":
            self._fullSchema[key] = newType
            return
        if oldType != "mixed":
            self._fullSchema[key] = "mixed"

    def _extractSchemaFromObj(self, data: Dict[str, Any], prefix: str, itemIndex: int) -> None:
        for key, value in data.items():
            newPrefix = f"{prefix}{key}" if prefix else key
            vtype = self.getStandardType(value)
            self._mergeType(newPrefix, vtype, itemIndex)
            if isinstance(value, dict):
                self._extractSchemaFromObj(value, f"{newPrefix}.", itemIndex)
            elif isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    if self.listPolicy == "first":
                        self._extractSchemaFromObj(first, f"{newPrefix}.", itemIndex)
                    else:
                        for elem in value:
                            if isinstance(elem, dict):
                                self._extractSchemaFromObj(elem, f"{newPrefix}.", itemIndex)
                elif isinstance(first, list):
                    if self.listPolicy == "first":
                        self._extractSchemaFromList(first, f"{newPrefix}.", itemIndex)
                    else:
                        for elem in value:
                            if isinstance(elem, list):
                                self._extractSchemaFromList(elem, f"{newPrefix}.", itemIndex)

    def _extractSchemaFromList(self, dataList: List[Any], prefix: str, itemIndex: int) -> None:
        if not dataList:
            return
        first = dataList[0]
        if isinstance(first, dict):
            if self.listPolicy == "first":
                self._extractSchemaFromObj(first, prefix, itemIndex)
            else:
                for elem in dataList:
                    if isinstance(elem, dict):
                        self._extractSchemaFromObj(elem, prefix, itemIndex)
        elif isinstance(first, list):
            if self.listPolicy == "first":
                self._extractSchemaFromList(first, prefix, itemIndex)
            else:
                for elem in dataList:
                    if isinstance(elem, list):
                        self._extractSchemaFromList(elem, prefix, itemIndex)

    def createSchemaFromData(self, data: Any) -> Dict[str, str]:
        self._processedFields.clear()
        self._fullSchema.clear()
        dataList = data if isinstance(data, list) else [data]
        if not dataList:
            raise ValueError("JSON data is empty")
        for i, item in enumerate(dataList, 1):
            if isinstance(item, dict):
                self._extractSchemaFromObj(item, prefix="", itemIndex=i)
        return dict(self._fullSchema)

    def schemaRun(self, segmentDict: Any) -> Dict[str, str]:
        return self.createSchemaFromData(segmentDict)
