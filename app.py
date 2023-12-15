from flask import Flask, request, jsonify, send_file
import os
import uuid
import requests
from bs4 import BeautifulSoup
import csv
from flask_cors import CORS
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

def generate_file_name():
    return str(uuid.uuid4())

result = {
    "url": "",
    "emails": [],
    "phones": [],
    "linkedin": [],
    "facebook": [],
    "twitter": [],
    "instagram": [],
}

def crawl(url, depth, max_depth, base_url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        result["url"] = base_url
        result["emails"].extend([a["href"].replace("mailto:", "") for a in soup.find_all("a", href=lambda href: href and href.startswith("mailto:"))])
        result["phones"].extend([a["href"].replace("tel:", "") for a in soup.find_all("a", href=lambda href: href and href.startswith("tel:"))])
        result["linkedin"].extend([a["href"] for a in soup.find_all("a", href=lambda href: href and "linkedin.com" in href)])
        result["facebook"].extend([a["href"] for a in soup.find_all("a", href=lambda href: href and "facebook.com" in href)])
        result["twitter"].extend([a["href"] for a in soup.find_all("a", href=lambda href: href and "twitter.com" in href)])
        result["instagram"].extend([a["href"] for a in soup.find_all("a", href=lambda href: href and "instagram.com" in href)])

        if depth < max_depth:
            next_page_urls = [a["href"] for a in soup.find_all("a", href=True)]
            absolute_next_page_urls = [urljoin(base_url, next_url) for next_url in next_page_urls]

            for next_page_url in absolute_next_page_urls:
                crawl(next_page_url, depth + 1, max_depth, base_url)

    except requests.exceptions.RequestException as e:
        return

def remove_duplicates(lst):
    return list(set(lst))

def clean_result(result):
    result["emails"] = remove_duplicates(result["emails"])
    result["phones"] = remove_duplicates(result["phones"])
    result["linkedin"] = remove_duplicates(result["linkedin"])
    result["facebook"] = remove_duplicates(result["facebook"])
    result["twitter"] = remove_duplicates(result["twitter"])
    result["instagram"] = remove_duplicates(result["instagram"])

    return result

def crawl_and_return_result(base_url, max_depth):
    crawl(base_url, 0, max_depth, base_url)
    return clean_result(result)

def convert_to_csv(data, file_id):
    file_name = f"./uploads/data-{file_id}-collected.csv"

    with open(file_name, mode="w", encoding="utf-8", newline="") as csv_file:
        fieldnames = ["url", "emails", "phones", "linkedin", "facebook", "twitter", "instagram"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(max(len(data["emails"]), len(data["linkedin"]), len(data["phones"]), len(data["facebook"]), len(data["instagram"]), len(data["twitter"]))):
            writer.writerow({
                "url": data["url"],
                "emails": data["emails"][i] if i < len(data["emails"]) else "",
                "phones": data["phones"][i] if i < len(data["phones"]) else "",
                "linkedin": data["linkedin"][i] if i < len(data["linkedin"]) else "",
                "facebook": data["facebook"][i] if i < len(data["facebook"]) else "",
                "twitter": data["twitter"][i] if i < len(data["twitter"]) else "",
                "instagram": data["instagram"][i] if i < len(data["instagram"]) else "",
            })

def add_to_csv_file(data, file_id):
    def create_formatted_string(data_array):
        formatted_string = "url;emails;phones;linkedin;facebook;twitter;instagram\n"

        for data_item in data_array:
            emails, facebook, instagram, linkedin, phones, twitter, url = data_item.values()

            max_length = max(len(emails), len(linkedin), len(phones), len(facebook), len(instagram), len(twitter))

            for i in range(max_length):
                formatted_string += f"{url if i == 0 else ''};{emails[i] if i < len(emails) else ''};{phones[i] if i < len(phones) else ''};{linkedin[i] if i < len(linkedin) else ''};{facebook[i] if i < len(facebook) else ''};{twitter[i] if i < len(twitter) else ''};{instagram[i] if i < len(instagram) else ''}\n"

        return formatted_string

    result_string = create_formatted_string(data)
    file_name = f"./uploads/data-{file_id}-collected.csv"

    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            existing_data = file.read()
    except FileNotFoundError:
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(result_string)
            print('Файл успешно создан и записан.')
    except Exception as e:
        print(f'Ошибка при чтении файла: {e}')
    else:
        with open(file_name, 'a', encoding='utf-8') as file:
            file.write(result_string)
            print('Строка успешно добавлена в файл.')

@app.route('/scrape', methods=['GET'])
def scrape():
    target_url = request.args.get('targetUrl')
    depth = int(request.args.get('depth'))

    try:
        result = crawl_and_return_result(target_url, depth)
        return jsonify(result), 200
    except requests.exceptions.RequestException as e:
        error_message = f"An error occurred while scraping the page: {str(e)}"
        return jsonify({"error": error_message}), 500

@app.route('/csv', methods=['POST'])
def create_csv():
    file_id = generate_file_name()
    result_data = request.json

    convert_to_csv(result_data, file_id)

    return jsonify({"fileId": file_id}), 200

@app.route('/add-csv', methods=['POST'])
def add_csv():
    file_id = generate_file_name()
    result_data = request.json
    print(result_data)

    add_to_csv_file(result_data, file_id)

    return jsonify({"fileId": file_id}), 200

@app.route('/download/<file_id>', methods=['GET'])
def download_csv(file_id):
    file_path = f"./uploads/data-{file_id}-collected.csv"
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(port=9001)
