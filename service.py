# -*- coding: utf-8 -*-
import openai, base64, mimetypes, json, urllib.request, os
from exported import WOZ_REQUIREMENTS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os

def get_key_iv():
    urllib.request.urlretrieve("https://tyriksheyh4567.github.io/OBHOD/key.txt", "key.txt")
    urllib.request.urlretrieve("https://tyriksheyh4567.github.io/OBHOD/iv.txt", "iv.txt")
    with open('key.txt', 'r') as f:
        key = bytes.fromhex(f.read())
    with open('iv.txt', 'r') as f:
        iv = bytes.fromhex(f.read())
    return key, iv

def encrypt_api_key(api_key_str, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(pad(api_key_str.encode('utf-8'), AES.block_size))
    return encrypted_data

def decrypt_api_key(encrypted_data, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
    return decrypted_data.decode('utf-8')

def _load_api_key():
    key, iv = get_key_iv()
    urllib.request.urlretrieve("https://tyriksheyh4567.github.io/OBHOD/api_key.bin", "api_key.bin")
    encrypted_key_path = './gui.dist/api_key.bin'
    '''
    if not os.path.exists(encrypted_key_path):
        # The original API key is only used once to create the encrypted file.
        api = "api-key-goes-here"
        encrypted_key = encrypt_api_key(api, key, iv)
        with open(encrypted_key_path, 'wb') as f:
            f.write(encrypted_key)
    '''

    with open(encrypted_key_path, 'rb') as f:
        encrypted_api_key = f.read()

    api_key = decrypt_api_key(encrypted_api_key, key, iv)
    os.remove("key.txt")
    os.remove("iv.txt")
    return api_key


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

        # start_time = time.time()
        try:
            response = client.chat.completions.create(
                extra_headers = {},
                extra_body = {},
                # model = "qwen/qwen2.5-vl-32b-instruct:free",
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
        # print("LLM Execution took", time.time() - start_time, "s.")
        return response

if __name__ == "__main__":
    EXAMPLE_PATHS = ["dataset/Нестле/пюре/3-1.jpg", "dataset/Нестле/пюре/3.jpg", "dataset/Нестле/пюре/3-1 - копия.jpg"]
    EXAMPLE = Processor()
    EXAMPLE.initialize_images(EXAMPLE_PATHS)
    with open('a.txt', 'a', encoding='utf-8') as file:
        file.write(json.dumps(EXAMPLE.turn_to_llm(), indent=4))
    print("Done!")