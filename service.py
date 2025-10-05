# -*- coding: utf-8 -*-
import openai, time, base64, mimetypes, json, os
from exported import WOZ_REQUIREMENTS


def _load_api_key():
    """Load OpenRouter / OpenAI API key securely.

    Priority:
      1. OPENROUTER_API_KEY (plain text) environment variable
      2. OPENROUTER_API_KEY_B64 (base64-encoded) environment variable
      3. .env file (requires python-dotenv) - same variable names as above

    Raises RuntimeError if key not found.
    """
    # 1) plain env var
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key.strip()

    # 2) base64 env var
    key_b64 = os.getenv("OPENROUTER_API_KEY_B64")
    if key_b64:
        try:
            return base64.b64decode(key_b64).decode("utf-8").strip()
        except Exception:
            pass

    # 3) try loading from .env if python-dotenv available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("OPENROUTER_API_KEY")
        if key:
            return key.strip()
        key_b64 = os.getenv("OPENROUTER_API_KEY_B64")
        if key_b64:
            return base64.b64decode(key_b64).decode("utf-8").strip()
    except Exception:
        # python-dotenv not installed or .env absent
        pass

    raise RuntimeError(
        "API key not found. Set OPENROUTER_API_KEY (plain) or OPENROUTER_API_KEY_B64 (base64) as environment variable."
    )


API_KEY = _load_api_key()

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)


json_template = {
    "name": "N/A",
    "category": "N/A",
    "characteristics": {
        "energy_value": "N/A",
        "sodium": "N/A",
        "total_sugar": "N/A",
        "free_sugar": "N/A",
        "total_protein": "N/A",
        "total_fat": "N/A",
        "fruit_content": "N/A",
        "age_marking": "N/A",
        "high_sugar_front_packaging": "false",
        "labeling": "true",
    },
    "additional_info": {
        "containings": "N/A",
        "description": "N/A",
        "manufactuer_address": "N/A",
        "storing_conditions": "N/A",
    }
}

def encode_image(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    if mime is None:
        mime = "image/jpeg"
    with open(path, "rb") as file:
        b64 = base64.b64encode(file.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"
    

class Processor:
    def __init__(self):
        self.encoded_images = []
    
    def initialize_images(self, image_paths):
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        
        self.encoded_images = []
        for image_path in image_paths:
            self.encoded_images.append(encode_image(image_path))
    
    def turn_to_llm(self):
        messages = [
            {"type": "text", "text": f"БАЗА ПРОДУКЦИИ Всемирной Организации Здравоохранения: {WOZ_REQUIREMENTS} НА ОСНОВЕ ИНФОРМАЦИИ И ТЕКСТА С ИЗОБРАЖЕНИЙ, заполни информацию о продукте по этой схеме {json.dumps(json_template)}. Определи к какой ЕДИНСТВЕННОЙ категории из БАЗЫ ПРОДУКТОВ относится продуктов, НАЙДИ СПИСОК ТРЕБОВАНИЙ ИМЕННО ДЛЯ ЭТОЙ ЧИСЛОВОЙ КАТЕГОРИИ И ДОБАВЬ РЕЗУЛЬТАТ СРАВНЕНИЯ ХАРАКТЕРИСТИК ПРОДУКТА С НИМ В ПОЛЕ comparsion JSON. Там должно быть true, если требования для искомой величины не определены или в норме для анализируемого продукта. false, если значения не в норме. NaN, если требование определено, а данные для этого продукта не найдены. ВЕРНИ ТОЛЬКО JSON ФАЙЛ, СОДЕРЖАЩИЙ ХАРАКТЕРИСТИКИ ПРОДУКТА И РЕЗУЛЬТАТ СРАВНЕНИЯ"}
        ]
        
        for image_path in self.encoded_images:
            messages.append({"type": "image_url", "image_url": {"url": image_path}})

        start_time = time.time()
        try:
            response = client.chat.completions.create(
                extra_headers = {},
                extra_body = {},
                #model = "qwen/qwen2.5-vl-32b-instruct:free",
                model = "mistralai/mistral-small-3.2-24b-instruct:free",
                messages=[{
                    "role": "user",
                    "content": messages,
                }],
            ).choices[0].message.content
            
            first_bracer = response.find("{")
            last_bracer = response.rfind("}")
            try:
                response = json.loads(response[first_bracer:last_bracer+1])
            except Exception as exception:
                print("Model`s output cannot be interpreted as JSON", exception)
                print(response)
                return json_template
            print(response)
        except Exception as exception:
            print("Exception occured on OpenRouter`s side:", exception)
            return json_template
        print("LLM Execution took", time.time() - start_time, "s.")
        return response

if __name__ == "__main__":
    EXAMPLE_PATHS = ["dataset/Нестле/пюре/3-1.jpg", "dataset/Нестле/пюре/3.jpg", "dataset/Нестле/пюре/3-1 - копия.jpg"]
    EXAMPLE = Processor()
    EXAMPLE.initialize_images(EXAMPLE_PATHS)
    with open('a.txt', 'a', encoding='utf-8') as file:
        file.write(json.dumps(EXAMPLE.turn_to_llm(), indent=4))
    print("Done!")