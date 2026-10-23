document.addEventListener("DOMContentLoaded", () => {
    // --- Cấu hình API (Giữ nguyên) ---
    const API_TOKEN = ""; // Điền token của bạn vào đây
    const API_BASE_URL = "http://127.0.0.1:8000";

    // --- Lấy các phần tử layout MỚI ---
    const appContainer = document.getElementById("appContainer");
    const chatBody = document.getElementById("chatBody");
    const chatForm = document.getElementById("chatForm");
    const textInput = document.getElementById("textInput");
    const sendBtn = chatForm.querySelector(".send-btn");
    
    // --- Lấy các phần tử file (Giữ nguyên) ---
    const fileInput = document.getElementById("fileUpload");
    const fileCard = document.getElementById("fileCard");
    const fileNameSpan = document.getElementById("fileName");
    const removeFileBtn = document.getElementById("removeFile");

    // --- Biến trạng thái ---
    let chatIsActive = false;
    let currentUserQuestion = ''; // Store current question for contribution
    let lastBotMessageElement = null; // Track last bot message for contribution button

    // --- HÀM KÍCH HOẠT LAYOUT CHAT ---
    function activateChatLayout() {
        if (!chatIsActive) {
            appContainer.classList.remove("layout-centered");
            appContainer.classList.add("layout-active");
            chatIsActive = true;
        }
    }

    // --- HÀM HIỂN THỊ NÚT GỬI ---
    textInput.addEventListener("input", () => {
        if (textInput.value.trim().length > 0) {
            sendBtn.style.display = "flex";
        } else {
            sendBtn.style.display = "none";
        }

        textInput.style.height = 'auto';
        textInput.style.height = (textInput.scrollHeight) + 'px';
    });

    // --- CÁC HÀM XỬ LÝ CHAT ---

    function typeWriter(element, text, delay = 10) {
        let i = 0;
        element.innerHTML = ""; 
        
        function typing() {
            if (i < text.length) {
                if (text.substring(i, i + 2) === "**") {
                    let boldEnd = text.indexOf("**", i + 2);
                    if (boldEnd !== -1) {
                        element.innerHTML += `<strong>${text.substring(i + 2, boldEnd)}</strong>`;
                        i = boldEnd + 2;
                    } else {
                        element.innerHTML += text.substring(i, i+2); i += 2;
                    }
                } else if (text.substring(i, i + 1) === "\n") {
                    element.innerHTML += "<br>"; i++;
                }
                else {
                    element.innerHTML += text.charAt(i); i++;
                }
                chatBody.scrollTop = chatBody.scrollHeight;
                setTimeout(typing, delay);
            }
        }
        typing();
    }

    function appendMessage(sender, text, useTypewriter = false) {
        // Tự động kích hoạt layout chat khi có tin nhắn
        activateChatLayout();

        const messageRow = document.createElement("div");
        const avatar = document.createElement("div");
        const messageBubble = document.createElement("div");

        messageRow.classList.add("message-row", `${sender}-row`);
        avatar.classList.add("avatar");
        messageBubble.classList.add(sender === 'bot' ? "bot-msg" : "user-msg");

        if (sender === 'bot' && useTypewriter) {
            typeWriter(messageBubble, text, 5);
        } else {
            const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>');
            messageBubble.innerHTML = formattedText;
        }

        messageRow.appendChild(avatar);
        messageRow.appendChild(messageBubble);
        
        // Add contribution button for bot messages
        if (sender === 'bot') {
            const messageActions = document.createElement("div");
            messageActions.classList.add("message-actions");
            
            const contributeBtn = document.createElement("button");
            contributeBtn.classList.add("btn-contribute");
            contributeBtn.innerHTML = 'Đóng góp';
            contributeBtn.onclick = () => openContributeModal(currentUserQuestion);
            
            messageActions.appendChild(contributeBtn);
            messageRow.appendChild(messageActions);
            
            lastBotMessageElement = messageRow;
        }
        
        chatBody.appendChild(messageRow);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function appendTyping() {
        activateChatLayout(); // Kích hoạt layout
        const typing = document.createElement("div");
        typing.classList.add("typing");
        typing.textContent = "AI đang xử lý...";
        chatBody.appendChild(typing);
        chatBody.scrollTop = chatBody.scrollHeight;
        return typing;
    }

    // --- CÁC HÀM XỬ LÝ FILE (Giữ nguyên) ---

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (file) {
            fileCard.style.display = "flex";
            fileNameSpan.textContent = file.name;
        } else {
            fileCard.style.display = "none";
        }
    });

    removeFileBtn.addEventListener("click", () => {
        fileInput.value = "";
        fileCard.style.display = "none";
    });

    // --- CÁC HÀM GỌI API (Giữ nguyên, nhưng thêm 'activateChatLayout') ---

    async function sendQuery(query) {
        activateChatLayout(); // Kích hoạt layout
        appendMessage("user", query);
        const typing = appendTyping();

        const headers = { "Content-Type": "application/json" };
        if (API_TOKEN) {
            headers["Authorization"] = `Bearer ${API_TOKEN}`;
        }

        try {
            console.log(`🔍 Fetching: ${API_BASE_URL}/api/v1/search/vector`);
            const response = await fetch(`${API_BASE_URL}/api/v1/search/vector`, {
                method: "POST",
                headers: headers,
                body: JSON.stringify({ query: query, top_k: 5, min_score: 0.5 }),
                timeout: 30000
            });
            
            const data = await response.json();
            typing.remove();

            // Debug: Log API response
            console.log("API Response:", data);
            if (data.result) {
                console.log("Context:", data.result.context);
                console.log("Category:", data.result.category);
            }

            if (response.ok && data.success) {
                let formattedResponse = "✨<strong>Kết quả tìm kiếm:</strong><br>";
                const result = data.result;
                
                if (result) {
                    
                    // Content from 'context' field (JSONB from DB)
                    const context = result.context || {};
                    const category = result.category || {};
                    
                    let hasContent = false;
                    
                    // Display metadata (category info) - all fields
                    // Removed Index display as per user request
                    // if (category['Index']) {
                    //     formattedResponse += `<small style="color: #666;">📑 Mục: ${category['Index']}</small><br>`;
                    // }
                    if (category['Level 1']) {
                        formattedResponse += `<strong>${category['Level 1']}</strong><br>`;
                        if (category['Level 2']) {
                            formattedResponse += `<em>${category['Level 2']}</em><br>`;
                        }
                    }
                    
                    // Display article content from context
                    if (context.Article) {
                        // Remove leading numbers like "1. " from Article
                        let article = context.Article;
                        article = article.replace(/^\d+\.\s*/, ''); // Remove "1. ", "2. " etc at start
                        formattedResponse += `<br>${article}<br>`;
                        hasContent = true;
                    }
                    
                    // Also display Content if it exists
                    if (context.Content) {
                        if (Array.isArray(context.Content)) {
                            formattedResponse += `<br>${context.Content.join('<br>')}<br>`;
                        } else if (typeof context.Content === 'string' && context.Content.trim()) {
                            formattedResponse += `<br>${context.Content}<br>`;
                        }
                        hasContent = true;
                    }
                    
                    if (!hasContent) {
                        formattedResponse += `<em>Không có nội dung trong kết quả</em><br>`;
                    }
                    
                    // Metadata footer
                    formattedResponse += `<br><small>Điểm: ${result.final_score?.toFixed(3) || result.base_score?.toFixed(3) || 'N/A'} - Nguồn: ${result.source}</small>`;
                } else {
                    formattedResponse += "Không tìm thấy kết quả nào phù hợp.";
                }
                appendMessage("bot", formattedResponse);
            } else if (!data.success) {
                appendMessage("bot", "✨<strong>Kết quả tìm kiếm:</strong><br>Không tìm thấy kết quả nào phù hợp.");
            } else {
                appendMessage("bot", `Lỗi: ${response.status} - ${data.detail || 'Không xác định'}`);
            }
        } catch (err) {
            typing.remove();
            
            // Detailed error logging
            console.error("❌ API Error:", err);
            console.error("   Name:", err.name);
            console.error("   Message:", err.message);
            console.error("   Stack:", err.stack);
            
            let errorMsg = "Không thể kết nối tới API!";
            let errorDetail = "";
            
            // Determine error type
            if (err.name === "TypeError") {
                if (err.message.includes("Failed to fetch")) {
                    errorMsg = "Lỗi mạng: Không thể kết nối tới server";
                    errorDetail = "Kiểm tra xem server có đang chạy không (http://localhost:8000)";
                } else if (err.message.includes("CORS")) {
                    errorMsg = "Lỗi CORS: Server không cho phép kết nối từ trang này";
                    errorDetail = "Kiểm tra cài đặt CORS trên server";
                } else if (err.message.includes("NetworkError")) {
                    errorMsg = "Lỗi mạng: Kết nối bị từ chối";
                    errorDetail = "Kiểm tra xem server có đang chạy trên port 8000 không";
                }
            } else if (err.name === "AbortError") {
                errorMsg = "Lỗi timeout: Server không phản hồi trong 30 giây";
                errorDetail = "Server có thể đang bận hoặc lag";
            }
            
            const fullErrorMsg = errorDetail 
                ? `⚠️ <strong>${errorMsg}</strong><br><small>${errorDetail}<br><br>Lỗi chi tiết: ${err.message}</small>`
                : `⚠️ <strong>Lỗi kết nối:</strong> ${err.message || errorMsg}`;
            
            appendMessage("bot", fullErrorMsg);
        }
    }

    async function sendFile(file) {
        activateChatLayout(); // Kích hoạt layout
        appendMessage("user", `Đã đính kèm: ${file.name}`);
        const typing = appendTyping();
        const formData = new FormData();
        formData.append("file", file);

        const headers = {};
        if (API_TOKEN) {
            headers["Authorization"] = `Bearer ${API_TOKEN}`;
        }

        try {
            console.log(`📄 Uploading PDF: ${file.name}`);
            const response = await fetch(`${API_BASE_URL}/process_pdf`, {
                method: "POST",
                headers: headers,
                body: formData,
                timeout: 60000
            });
            const data = await response.json();
            typing.remove();

            if (response.ok && data.status === "success") {
                if (data.checkstatus === "ok") {
                    appendMessage("bot", `✨**Phân tích PDF thành công!**\nChủ đề: **${data.category}**.\n\n**Tóm tắt:**\n${data.summary}`, true);
                } else {
                    appendMessage("bot", `⚠️**Không thể xử lý PDF**\nLý do: ${data.category}`, true);
                }  
            } else {
                appendMessage("bot", `❌ **Lỗi:** ${data.detail || "Không rõ"}`, true);
            }
        } catch (err) {
            typing.remove();
            
            console.error("❌ PDF Upload Error:", err);
            console.error("   Message:", err.message);
            
            let errorMsg = "Lỗi tải lên: Không thể kết nối tới API!";
            if (err.name === "TypeError" && err.message.includes("Failed to fetch")) {
                errorMsg = "Lỗi mạng: Không thể kết nối tới server";
            } else if (err.name === "AbortError") {
                errorMsg = "Lỗi timeout: Server không phản hồi";
            }
            
            appendMessage("bot", `⚠️ **${errorMsg}** <br><small>Chi tiết: ${err.message}</small>`, true);
        }
    }

    // --- KIỂM TRA KẾT NỐI SERVER KHI LOAD TRANG ---
    window.addEventListener('load', () => {
        console.log(`📍 Frontend URL: ${window.location.href}`);
        console.log(`📍 API URL: ${API_BASE_URL}`);
        console.log(`🔍 Kiểm tra kết nối server...`);
        
        fetch(`${API_BASE_URL}/`, { method: 'GET', timeout: 5000 })
            .then(r => {
                console.log(`✅ Server hoạt động (Status: ${r.status})`);
            })
            .catch(e => {
                console.error(`⚠️ Không thể kết nối tới server: ${e.message}`);
                // Não show error to user on page load, they'll see it when they try to search
            });
    });

    // --- HÀM SUBMIT FORM CHÍNH ---
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        sendBtn.disabled = true;

        const file = fileInput.files[0];
        const query = textInput.value.trim();

        // 🔹 Xoá input NGAY khi người dùng nhấn gửi
        textInput.value = "";
        requestAnimationFrame(() => {
            textInput.style.height = 'auto';
        });
        sendBtn.style.display = 'none';

        try {
            if (file) {
                await sendFile(file);
                fileInput.value = "";
                fileCard.style.display = "none";
            } else if (query) {
                currentUserQuestion = query; // Store for contribution
                await sendQuery(query);
            } else {
                return;
            }
        } finally {
            sendBtn.disabled = false;
        }
    });

    // Cho phép gửi bằng Enter (và Shift+Enter để xuống dòng)
    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.requestSubmit();
        }
    });

    // --- CONTRIBUTION FEATURE ---
    
    // Contribution modal elements
    const contributeModal = document.getElementById('contribute-modal');
    const originalQuestionEl = document.getElementById('original-question');
    const contributionTextarea = document.getElementById('contribution-text');
    const charCountEl = document.getElementById('char-count');
    
    // Character counter
    contributionTextarea.addEventListener('input', function() {
        const count = this.value.length;
        charCountEl.textContent = count;
    });
    
    // Make functions global so onclick can access them
    window.openContributeModal = function(userQuestion) {
        originalQuestionEl.textContent = userQuestion || currentUserQuestion;
        contributionTextarea.value = '';
        charCountEl.textContent = '0';
        contributeModal.style.display = 'flex';
    };
    
    window.closeContributeModal = function() {
        contributeModal.style.display = 'none';
    };
    
    window.submitContribution = async function() {
        const contributionText = contributionTextarea.value.trim();
        
        // Validation
        if (!contributionText) {
            showToast('Vui lòng nhập nội dung đóng góp', 'error');
            return;
        }
        
        if (contributionText.length < 10) {
            showToast('Nội dung đóng góp quá ngắn. Vui lòng nhập ít nhất 10 ký tự.', 'error');
            return;
        }
        
        const submitBtn = document.querySelector('.btn-submit');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Đang gửi...';
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/contribution`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_question: originalQuestionEl.textContent,
                    user_contribution: contributionText,
                    metadata: {
                        user_id: 'web_user_' + Date.now(),
                        source: 'web_chat',
                        timestamp: new Date().toISOString()
                    }
                })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                showToast('Cảm ơn bạn đã đóng góp! Thông tin của bạn sẽ giúp cải thiện hệ thống.', 'success');
                closeContributeModal();
                
                // Mark button as contributed
                if (lastBotMessageElement) {
                    const btn = lastBotMessageElement.querySelector('.btn-contribute');
                    if (btn) {
                        btn.innerHTML = '✅ Đã đóng góp';
                        btn.classList.add('contributed');
                        btn.disabled = true;
                    }
                }
            } else {
                showToast('Có lỗi xảy ra. Vui lòng thử lại sau.', 'error');
            }
        } catch (error) {
            console.error('Contribution error:', error);
            showToast('Không thể kết nối đến server. Vui lòng kiểm tra kết nối mạng.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Gửi đóng góp';
        }
    };
    
    // Toast notification function
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

});