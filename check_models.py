import google.generativeai as genai

def list_my_models():
    # 執行時要求使用者輸入 API Key
    api_key = input("🔑 請輸入您的 Google Gemini API Key：").strip()
    
    if not api_key:
        print("⚠️ 未輸入 API Key，程式結束。")
        return

    genai.configure(api_key=api_key)
    print("\n🔍 正在連線查詢您可使用的模型清單...\n")
    
    try:
        # 取得所有模型，並篩選出支援「文字生成 (generateContent)」的模型
        available_models = [
            m.name for m in genai.list_models() 
            if 'generateContent' in m.supported_generation_methods
        ]
        
        print("✅ 這把 API Key 支援以下模型：")
        for name in available_models:
            print(f" - {name}")
            
    except Exception as e:
        print(f"❌ 查詢失敗，請確認 API Key 是否有效。錯誤訊息：\n{e}")

if __name__ == "__main__":
    list_my_models()