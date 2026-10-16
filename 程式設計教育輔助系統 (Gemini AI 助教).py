import os
import sys
import webbrowser
import gradio as gr
import google.generativeai as genai

# ==========================================
# 1. System Prompt 範本定義
# ==========================================
PROMPT_EXPLAIN_TEMPLATE = """你是一位具備豐富教學經驗的程式設計助教。請以初學者能理解的引導式口吻，解釋以下程式碼的運作邏輯。

要求：
1. 先用一句話總結這段程式碼的功能。
2. 逐段/逐行解釋核心邏輯，特別標註使用到的關鍵技巧。
3. 舉出一個生活化的比喻來幫助理解該邏輯。

[輸入程式碼]：
{code}
"""

PROMPT_CORRECT_TEMPLATE = """學生提交了一段有 Bug 的程式碼，並遇到了執行錯誤/非預期輸出。你的任務是引導學生找出錯誤，而不是直接把答案給他。

要求：
1. 指出位置： 明確說明錯誤發生在哪一行或哪一個區塊。
2. 解釋成因： 說明為什麼會發生這個錯誤。
3. 給予提示： 提供 1 到 2 個修改方向或反思問題，引導學生自行修正，嚴禁直接輸出修正後的完整程式碼。

[錯誤訊息/預期與實際輸出]：
{error_info}

[輸入程式碼]：
{code}
"""

PROMPT_PRACTICE_TEMPLATE = """請分析以下程式碼所包含的「核心語法」與「演算法邏輯」。根據分析結果，生成一道難度相當、但應用場景完全不同的全新練習題。

要求：
1. 知識點萃取： 列出這題測驗了哪些程式概念。
2. 情境包裝： 設計一個全新的題目情境。
3. 題目敘述： 包含清晰的題目說明、輸入格式、輸出格式。
4. 測資提供： 提供至少兩組 Test Cases。
5. 隱藏解答： 提供一份標準的參考程式碼解答（請使用 `<details><summary>點擊展開參考解答</summary>\n\n```python\n# 解答內容\n```\n</details>` 的 Markdown 語法封裝）。

[原始程式碼]：
{code}
"""

# ==========================================
# 2. 核心功能函式
# ==========================================
def get_code_content(source_choice, code_text, uploaded_file):
    if "上傳檔案" in source_choice:
        if uploaded_file is not None:
            try:
                file_path = uploaded_file.name if hasattr(uploaded_file, "name") else str(uploaded_file)
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"# 讀取檔案失敗: {str(e)}"
        else:
            return ""
    else:
        return code_text

def call_gemini(api_key, model_name, prompt):
    if not api_key or not api_key.strip():
        return "⚠️ 請先輸入您的 Google Gemini API Key！"
    try:
        genai.configure(api_key=api_key.strip())
        clean_name = model_name.replace("models/", "").strip()
        model = genai.GenerativeModel(clean_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 呼叫 API 時發生錯誤：{str(e)}"

# ==========================================
# 3. 按鈕處理邏輯
# ==========================================
def get_final_model(free_model, paid_model, model_tier_choice):
    model = paid_model if "右側" in model_tier_choice else free_model
    if model == "(請先載入模型)" or not model or model == "無可用模型":
        return None
    return model

def handle_explain(api_key, free_model, paid_model, model_tier_choice, source_choice, code_text, uploaded_file):
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在為您解析程式碼，請稍候...</p></div>"
    
    final_model = get_final_model(free_model, paid_model, model_tier_choice)
    if not final_model:
        yield "⚠️ **請先貼上 API Key 並點擊上方的「🔄 載入可用模型」按鈕！**"
        return

    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    prompt = PROMPT_EXPLAIN_TEMPLATE.format(code=code)
    yield call_gemini(api_key, final_model, prompt)

def handle_correct(api_key, free_model, paid_model, model_tier_choice, source_choice, code_text, uploaded_file, error_info):
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在幫您尋找 Bug 與除錯，請稍候...</p></div>"
    
    final_model = get_final_model(free_model, paid_model, model_tier_choice)
    if not final_model:
        yield "⚠️ **請先貼上 API Key 並點擊上方的「🔄 載入可用模型」按鈕！**"
        return

    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    err_msg = error_info.strip() if error_info and error_info.strip() else "無提供具體錯誤訊息，請針對程式碼進行潛在 Bug 預測。"
    prompt = PROMPT_CORRECT_TEMPLATE.format(code=code, error_info=err_msg)
    yield call_gemini(api_key, final_model, prompt)

def handle_practice(api_key, free_model, paid_model, model_tier_choice, source_choice, code_text, uploaded_file):
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在為您設計專屬練習題，請稍候...</p></div>"
    
    final_model = get_final_model(free_model, paid_model, model_tier_choice)
    if not final_model:
        yield "⚠️ **請先貼上 API Key 並點擊上方的「🔄 載入可用模型」按鈕！**"
        return

    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    prompt = PROMPT_PRACTICE_TEMPLATE.format(code=code)
    yield call_gemini(api_key, final_model, prompt)

# ==========================================
# 4. 前端網頁介面與排版 (大幅精簡版)
# ==========================================
with gr.Blocks(title="程式設計教育輔助系統", theme=gr.themes.Soft(), css="""
    /* 1. 精準點名並強制隱藏 gr.Code 內部右側的所有按鈕與圖示 */
    .gr-code button, 
    .gr-code .icon-button, 
    .gr-code [data-testid="block-info"] + div button,
    .gr-code .cm-button { 
        display: none !important; 
    }
    
    /* 2. 徹底清空 gr.Code 的頂部邊框，讓它與您的自訂工具列緊密無縫 */
    .gr-code {
        border-top: none !important;
        border-top-left-radius: 0 !important;
        border-top-right-radius: 0 !important;
    }
""") as demo:
    gr.Markdown(
        """
        # 🎓 程式設計教育輔助系統 (Gemini AI 助教)
        **專為程式初學者設計！** 支援手動貼上程式碼或直接上傳程式碼檔案。<br>
        📢 **【免費使用宣告】** 本系統主打「免綁卡、純免費學習」。預設採用 Google 官方高額免費配額的 **Flash 系列模型**。
        """
    )

    with gr.Row():
        # 左半邊：設定與輸入區
        with gr.Column(scale=1):
            
            # --- 區塊 1：API 與模型設定 ---
            with gr.Group():
                with gr.Row():
                    api_key_input = gr.Textbox(label="Google Gemini API Key", type="password", scale=4)
                    btn_load_models = gr.Button("🔄 載入可用模型", variant="secondary", scale=1)
                
                status_text = gr.Markdown(" ")
                model_tier_radio = gr.Radio(
                    label="🎯 模型等級 (強制二選一)",
                    choices=["🟢 左側：免費教育模型", "🔴 右側：進階付費模型"],
                    value="🟢 左側：免費教育模型"
                )
                with gr.Row():
                    free_model_selector = gr.Dropdown(label="🟢 免費教育模型", choices=["(請先載入模型)"], value="(請先載入模型)", scale=1)
                    paid_model_selector = gr.Dropdown(label="🔴 進階付費模型", choices=["(請先載入模型)"], value="(請先載入模型)", scale=1)

            # --- 區塊 2：程式碼輸入區 ---
           # --- 區塊 2-1：程式碼來源與上傳區 ---
            with gr.Group():
                source_radio = gr.Radio(["📝 直接貼上", "📁 上傳檔案"], label="程式碼來源", value="📝 直接貼上")
                file_uploader = gr.File(label="📁 上傳檔案 (.py, .cpp, .txt 等)")
                
            # --- 區塊 2-2：程式碼編輯區 ---
            with gr.Group():
                # 將標題與四個功能統整成一列自訂工具列，顏色與上方完美同步
                with gr.Row(equal_height=True):
                    gr.Markdown(
                        """
                        <div style="
                            background-color: #7B61FF; 
                            color: white; 
                            padding: 6px 14px; 
                            border-radius: 8px; 
                            font-size: 14px; 
                            font-weight: bold; 
                            display: inline-block;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        ">
                            &lt;/&gt; 程式碼編輯區
                        </div>
                        """
                    ) 
                    btn_download_code = gr.Button("📥 下載", size="sm", scale=0, min_width=70)
                    btn_copy_code = gr.Button("📄 複製", size="sm", scale=0, min_width=70)
                    btn_paste_code = gr.Button("📋 貼上", size="sm", scale=0, min_width=70)
                    btn_clear_code = gr.Button("🗑️ 清除", size="sm", scale=0, min_width=70)

                # 確保完全隱藏預設標籤，只留下乾淨的編輯器本體
                code_input = gr.Code(
                    label="", 
                    show_label=False, 
                    language="python", 
                    lines=8
                )

            # --- 區塊 2-3：錯誤訊息輸入區 ---
            with gr.Group():
                gr.Markdown(
                    """
                    <div style="
                        background-color: #7B61FF; 
                        color: white; 
                        padding: 6px 14px; 
                        border-radius: 8px; 
                        font-size: 14px; 
                        font-weight: bold; 
                        display: inline-block;
                        margin-bottom: 5px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    ">
                        ⚠️ ［選填］錯誤修改訊息 / 預期輸出 (用於功能)
                    </div>
                    """
                )
                error_input = gr.Textbox(
                    label="", 
                    show_label=False, 
                    lines=2,
                    placeholder="在此貼上執行錯誤訊息、Traceback 或預期與實際輸出的差異..."
                )

            # --- 區塊 3：執行按鈕 ---
            with gr.Row():
                btn_explain = gr.Button("💡 1. 解釋功能", variant="primary")
                btn_correct = gr.Button("🛠️ 2. 更正功能", variant="primary")
                btn_practice = gr.Button("📝 3. 練習功能", variant="primary")

        # 右半邊：AI 回應結果區
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI 助教回應結果")
            output_markdown = gr.Markdown(
                value="<div style='min-height: 500px; padding: 10px; color: gray;'>*點擊左側按鈕後，回應結果將顯示於此...*</div>"
            )

    # ==========================================
    # 5. 事件與 JavaScript 綁定 (已加入模型智慧過濾)
    # ==========================================
    def fetch_and_split_models(api_key):
        if not api_key or not api_key.strip():
            return gr.update(), gr.update(), "⚠️ **請先貼上 API Key！**"
        try:
            genai.configure(api_key=api_key.strip())
            free_models, paid_models = [], []
            
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    name_lower = name.lower()
                    
                    # 🚫 濾除程式教學完全用不到的非文字/影像生成、語音、影片或嵌入模型
                    unwanted_keywords = ['imagen', 'veo', 'audio', 'tts', 'embedding', 'chirp', 'vision-only','image','2.5']
                    if any(kw in name_lower for kw in unwanted_keywords):
                        continue
                        
                    # 🟢 分類：帶有 flash 的歸類為免費教育模型，其餘歸類為進階付費模型
                    if "flash" in name_lower:
                        free_models.append(name)
                    else:
                        paid_models.append(name)
            
            if not free_models and not paid_models:
                return gr.update(), gr.update(), "⚠️ **找不到支援的模型。**"
                
            def_free = free_models[0] if free_models else None
            def_paid = paid_models[0] if paid_models else "無可用模型"
            return gr.Dropdown(choices=free_models, value=def_free), gr.Dropdown(choices=paid_models, value=def_paid), "✅ **模型載入成功（已自動濾除無關模型）！**"
        except Exception as e:
            return gr.update(), gr.update(), f"❌ **載入失敗：** {str(e)}"

    btn_load_models.click(fn=fetch_and_split_models, inputs=[api_key_input], outputs=[free_model_selector, paid_model_selector, status_text])
    
    # ==========================================
    # 🌟 自訂工具列：下載、複製、貼上、清除 綁定
    # ==========================================
    
    # 下載：利用 Blob 建立暫存文字檔並觸發瀏覽器下載
    btn_download_code.click(
        fn=None, inputs=[code_input], outputs=[code_input],
        js="""
        (code) => {
            if (!code) { alert('⚠️ 沒有程式碼可以下載！'); return code; }
            const blob = new Blob([code], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'code_snippet.py';
            a.click();
            URL.revokeObjectURL(url);
            return code;
        }
        """
    )

    # 複製：將目前輸入框的內容寫入剪貼簿
    btn_copy_code.click(
        fn=None, inputs=[code_input], outputs=[code_input],
        js="""
        async (code) => {
            if (!code) { alert('⚠️ 沒有程式碼可以複製！'); return code; }
            try {
                await navigator.clipboard.writeText(code);
                alert('✅ 程式碼已成功複製！');
            } catch (err) {
                alert('❌ 瀏覽器封鎖了複製功能，請手動全選複製。');
            }
            return code;
        }
        """
    )

    # 貼上：讀取剪貼簿並覆蓋輸入框
    btn_paste_code.click(
        fn=None, inputs=[code_input], outputs=[code_input], 
        js="""
        async (current_text) => { 
            try { 
                return await navigator.clipboard.readText(); 
            } catch(e) { 
                alert('⚠️ 瀏覽器安全限制，無法自動讀取剪貼簿！請直接按 Ctrl+V 貼上。'); 
                return current_text; 
            } 
        }
        """
    )
    
    # 清除：直接將內容設為空字串
    btn_clear_code.click(fn=lambda: "", inputs=None, outputs=[code_input])

    # 執行按鈕綁定
    common_inputs = [api_key_input, free_model_selector, paid_model_selector, model_tier_radio, source_radio, code_input, file_uploader]
    btn_explain.click(fn=handle_explain, inputs=common_inputs, outputs=[output_markdown])
    btn_correct.click(fn=handle_correct, inputs=common_inputs + [error_input], outputs=[output_markdown])
    btn_practice.click(fn=handle_practice, inputs=common_inputs, outputs=[output_markdown])

if __name__ == "__main__":
    demo.launch(inbrowser=True)