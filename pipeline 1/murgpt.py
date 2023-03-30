import docx 
import os
from scipy.spatial.distance import cosine
from openai.embeddings_utils import distances_from_embeddings
import openai

openai.api_key = "<KEY>"
get_counts_token = lambda encoding, str: len(encoding.encode(str)) # коллисество токенов в тексте


def get_list_files(path, extensions):
    """
    Получаем список файлов с расширениями из extensions по пути patch
    Args:
        path (str):путь к директории
        extensions (list): массив расширений ['.txt', '.docx' ... ]
    Returns:
        list: пути подходящих файлов
    """
    names_file = []
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            split_tup = os.path.splitext(file)
            if split_tup[1] in extensions:
                names_file.append(os.path.join(path, file))
    return names_file



def read_docs(docs_patch):
    """Получаем информацию по заголовкам из документа
    docs_patch (list): список путей к файлам

    Returns:
        Map: словарь - заголовок->объект 
    """
    info = {}
    struct = {}
    info['start'] = "" # для шапок и вводных частей документа

    for patch in docs_patch:
        doc = docx.Document(patch)
        f = False

        
        head_title = ""
        for paragraph in doc.paragraphs:
            
            if (paragraph.style.name == 'Heading 2'):
                f = True                                                    # метка - встретили уже один headline 2
                next_title_text = head_title + " " + paragraph.text
                info[next_title_text] = ""
 
                if head_title in struct:
                    struct[head_title].append(paragraph.text)               # добавляем в структуру заголовок
                else:
                    struct[next_title_text] = [paragraph.text]


            elif (paragraph.style.name == 'Heading 1'):
                head_title = paragraph.text     
                info[head_title] = ""
                struct[head_title] = []

            elif f:
                info[next_title_text] += paragraph.text

            else:
                struct['start'] = []
                info['start'] += paragraph.text

    return {'content': info,  'struct': struct}



def create_context_1ver(question, df, max_len=1800, size="ada"):
    """
    Create a context for a question by finding the most similar context from the dataframe
    """

    # Get the embeddings for the question
    q_embeddings = openai.Embedding.create(input=question, engine='text-embedding-ada-002')['data'][0]['embedding']

    # Get the distances from the embeddings
    df['distances'] = distances_from_embeddings(q_embeddings, df['embeddings'].values, distance_metric='cosine')

    returns = []
    cur_len = 0

    # Sort by distance and add the text to the context until the context is too long
    # Этот алгоритм потом можно улучшить, но а пока мы просто смотрим на топ 1
    for i, row in df.sort_values('distances', ascending=True).iterrows():
        # Add the length of the text to the current length
        #cur_len += row['n_tokens'] + 4

        # If the context is too long, break
        #if cur_len > max_len:
        #    break
        
        # Else add it to the text that is being returned
        returns.append(row["content"])
        break

    # Return the context
    return "\n\n###\n\n".join(returns)



def get_answer(data):
    text = data['choices'][0]['message']['content']
    role = data['choices'][0]['message']['role']
    total_tokens = data["usage"]['total_tokens']

    return role + ': ' + text 



def generate_answer(QUESTION, information, mes={}):
    mes = [
        {"role": "system", "content": "Привет! Ты ассистент помошник по использованию програмного продукта 'Дозор' \
         'Дозор'. Будь вежлив и краток. Здоровайся с каждым пользователем!"},
        {"role": "user", "content": "Главное не отвечай ничего лишнего. Говори только о том, что знаешь."},
        {"role": "user", "content": " Что ты знаешь об  'Дозор'?"},
        {"role": "assistant", "content": "Я пользуюсь только этой информацией: " +information},
        {"role": "user", "content": QUESTION},     
    ]

    response = openai.ChatCompletion.create(
         model="gpt-3.5-turbo",
        messages= mes
    )
    answer = get_answer(response)
    return answer



def emb_to_list(text):
    parse = text.strip('[]').replace(' ', '').split(',')
    return list(map(float, parse))