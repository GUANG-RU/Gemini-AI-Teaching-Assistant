import os
import sys
import webbrowser
import gradio as gr
import google.generativeai as genai

# ==========================================
# 1. System Prompt 範本定義 (這是發送給 AI 的核心指令字串，必須保留)
# ==========================================
PROMPT_EXPLAIN_TEMPLATE = """你是一位具備豐富教學經驗的程式設計助教。請以初學者能理解的引導式口吻，解釋以下程式碼的運作邏輯。

要求：
1. 先用一句話總結這段程式碼的功能。
2. 逐段/逐行解釋核心邏輯，特別標註使用到的關鍵技巧（例如：指標操作、陣列走訪、遞迴等）。
3. 舉出一個生活化的比喻來幫助理解該邏輯。

[輸入程式碼]：
{code}
"""

PROMPT_CORRECT_TEMPLATE = """學生提交了一段有 Bug 的程式碼，並遇到了執行錯誤/非預期輸出。你的任務是引導學生找出錯誤，而不是直接把答案給他。

要求：
1. 指出位置： 明確說明錯誤發生在哪一行或哪一個區塊。
2. 解釋成因： 說明為什麼會發生這個錯誤（例如：陣列越界、變數未初始化、型別不匹配）。
3. 給予提示： 提供 1 到 2 個修改方向或反思問題，引導學生自行修正，嚴禁直接輸出修正後的完整程式碼。

[錯誤訊息/預期與實際輸出]：
{error_info}

[輸入程式碼]：
{code}
"""

PROMPT_PRACTICE_TEMPLATE = """請分析以下程式碼所包含的「核心語法」與「演算法邏輯」。根據分析結果，生成一道難度相當、但應用場景完全不同的全新練習題。

要求：
1. 知識點萃取： 列出這題測驗了哪些程式概念。
2. 情境包裝： 設計一個全新的題目情境（例如將「計算學生成績平均」改為「計算購物車商品總價」）。
3. 題目敘述： 包含清晰的題目說明、輸入格式、輸出格式。
4. 測資提供： 提供至少兩組 Test Cases（包含 Input 與預期 Output）。
5. 隱藏解答： 提供一份標準的參考程式碼解答（請放在回應的最底部，並加上標示以便系統後續隱藏或展開，請使用 `<details><summary>點擊展開參考解答</summary>\n\n```python\n# 解答內容\n```\n</details>` 的 Markdown 語法封裝）。

[原始程式碼]：
{code}
"""

# ==========================================
# 2. 核心功能函式 (處理檔案讀取與 Gemini API 呼叫)
# ==========================================
def get_code_content(source_choice, code_text, uploaded_file):
    """根據使用者的選擇，讀取對應的程式碼內容"""
    # 如果使用者選擇「上傳檔案」
    if source_choice == "📁 上傳檔案":
        if uploaded_file is not None:
            try:
                file_path = uploaded_file.name if hasattr(uploaded_file, "name") else str(uploaded_file)
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"# 讀取檔案失敗: {str(e)}"
        else:
            return "" # 如果選了上傳檔案卻沒上傳，回傳空字串讓後續擋下
            
    # 如果使用者選擇「直接貼上」
    else:
        return code_text

def call_gemini(api_key, model_name, prompt):
    """呼叫 Gemini API 進行內容生成"""
    if not api_key or not api_key.strip():
        return "⚠️ 請先輸入您的 Google Gemini API Key！"
    try:
        genai.configure(api_key=api_key.strip())
        
        # 確保模型名稱帶有 models/ 前綴
        target_model = model_name if model_name.startswith("models/") else f"models/{model_name}"
        model = genai.GenerativeModel(target_model)
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ 呼叫 API 時發生錯誤：{str(e)}"

# ==========================================
# 3. 按鈕處理邏輯 (結合使用者輸入與 Prompt 傳送給 AI)
# ==========================================
def handle_explain(api_key, model_name, source_choice, code_text, uploaded_file):
    # 點擊瞬間，畫面先顯示 Thinking 動畫文字
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在為您解析程式碼，請稍候...</p></div>"
    
    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    prompt = PROMPT_EXPLAIN_TEMPLATE.format(code=code)
    # API 處理完畢後，輸出最終結果
    yield call_gemini(api_key, model_name, prompt)

def handle_correct(api_key, model_name, source_choice, code_text, uploaded_file, error_info):
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在幫您尋找 Bug 與除錯，請稍候...</p></div>"
    
    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    err_msg = error_info.strip() if error_info and error_info.strip() else "無提供具體錯誤訊息，請針對程式碼進行潛在 Bug 預測。"
    prompt = PROMPT_CORRECT_TEMPLATE.format(code=code, error_info=err_msg)
    yield call_gemini(api_key, model_name, prompt)

def handle_practice(api_key, model_name, source_choice, code_text, uploaded_file):
    yield "<div style='min-height: 500px; padding: 10px; color: gray;'><h3>🤖 Thinking...</h3><p>AI 助教正在為您設計專屬練習題，請稍候...</p></div>"
    
    code = get_code_content(source_choice, code_text, uploaded_file)
    if not code or not code.strip():
        yield "⚠️ 請確實依據您的選擇輸入程式碼或上傳檔案！"
        return
        
    prompt = PROMPT_PRACTICE_TEMPLATE.format(code=code)
    yield call_gemini(api_key, model_name, prompt)

# ==========================================
# 4. 建立 Gradio 前端網頁介面
# ==========================================
with gr.Blocks(title="程式設計教育輔助系統", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # 🎓 程式設計教育輔助系統 (Gemini AI 助教)
        **執行 Python 腳本後會自動開啟網頁！** 支援手動貼上程式碼或直接上傳程式碼檔案。
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ 系統設定")
            api_key_input = gr.Textbox(
                label="Google Gemini API Key",
                placeholder="貼上您的 Gemini API Key...",
                type="password"
            )
            
            # 預設改為 gemini-1.5-flash 模型以節省額度，
            # 此模型 models/gemini-2.5-flash 已不再對新使用者開放。
            # 請將您的程式碼更新為使用 models/gemini-3.8-flash 以取得最新功能和改進。
            # 我們建議您使用 Interactions API（https://ai.google.dev/gemini-api/docs/get-started）。 
            # 對就是這樣所以不要太相信AI謝謝
            model_selector = gr.Dropdown(
                label="選擇 Gemini 模型版本",
                choices=["gemini-3.8-flash", "gemini-3.8-pro"],
                value="gemini-3.8-flash"
            )

            gr.Markdown("### 📝 程式碼輸入與上傳")

            # 新增這行：讓使用者明確選擇來源
            source_radio = gr.Radio(
                label="請選擇程式碼來源",
                choices=["📝 直接貼上", "📁 上傳檔案"],
                value="📝 直接貼上",
                interactive=True
            )
            file_uploader = gr.File(
                label="📁 上傳程式碼檔案 (.py, .cpp, .c, .java, .txt)",
                file_types=[".py", ".cpp", ".c", ".java", ".txt", ".js", ".cs"]
            )
            code_input = gr.Code(
                label="或直接貼上程式碼：",
                language="python",
                lines=10,
                value="def calculate_average(scores):\n    total = 0\n    for score in scores:\n        total += score\n    return total / len(scores)"
            )
            error_input = gr.Textbox(
                label="［選擇性］錯誤訊息 / 預期與實際輸出（更正功能使用）：",
                placeholder="例如: ZeroDivisionError: division by zero",
                lines=3
            )

            gr.Markdown("### ⚡ 點擊功能按鈕執行")
            with gr.Row():
                btn_explain = gr.Button("💡 1. 解釋功能", variant="primary")
                btn_correct = gr.Button("🛠️ 2. 更正功能", variant="primary")
                btn_practice = gr.Button("📝 3. 練習功能", variant="primary")

        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI 助教回應結果")
            # 加入 min-height 撐開預設高度，讓載入動畫有足夠空間顯示
            output_markdown = gr.Markdown(
                value="<div style='min-height: 500px; padding: 10px; color: gray;'>*點擊左側按鈕後，回應結果將顯示於此...*</div>"
            )

    # 事件綁定 (連結按鈕與後端功能)
    btn_explain.click(
        fn=handle_explain,
        # 注意：source_radio 必須加在 model_selector 和 code_input 之間，順序要與函式參數一致
        inputs=[api_key_input, model_selector, source_radio, code_input, file_uploader],
        outputs=[output_markdown]
    )

    btn_correct.click(
        fn=handle_correct,
        inputs=[api_key_input, model_selector, code_input, file_uploader, error_input],
        outputs=[output_markdown]
    )

    btn_practice.click(
        fn=handle_practice,
        inputs=[api_key_input, model_selector, code_input, file_uploader],
        outputs=[output_markdown]
    )

if __name__ == "__main__":
    # 自動開啟瀏覽器網頁
    demo.launch(inbrowser=True)