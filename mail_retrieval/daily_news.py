import json

from datetime import datetime
from explorer import Explorer
from exporter import Exporter
from langchain_core.documents import Document
from parser import Parser
from parser import Section
from parser import News


def _filter_sections_for_export(sections: list[Section]):
    """
    Filters out some sections which is not required to store on the vector store
    """
    not_allowed_sections = ["BUGÜNKÜ DESTEKÇIMIZ", "HAFTANIN OKUMASI", "AJANDA", "AYRILMADAN ÖNCE"]
    return [section for section in sections if section.title not in not_allowed_sections]


def _construct_document_from_news(news:News, section_name:str, date:str):
    """
    Creates a single Document object from a single news
    """
    return Document(
        id="",
        page_content=news.get_lines_for_document(),
        metadata={
            "section_title": section_name,
            "date_str": date
        }
    )


def _construct_documents_from_sections(section_list:list[Section], date_str: str):
    """
    Given a Section object, creates documents to provide to the vector store
    from the news array of that section
    """
    documents = []
    for section in section_list:
        for news in section.news:
            documents.append(_construct_document_from_news(news, section.get_title_for_document(), date_str))

    return documents

def _construct_output_file(section_list:list[Section]):
    """
    Given a Section object, creates a json file to generate as output
    from the news array of that section
    """
    sections_str = []
    for section in section_list:
        
        if len(section.news) == 0:
            continue

        section_texts = []
        for news in section.news:
            section_texts.append(news.get_lines_for_document())

        sections_str.append({
            "section_title": section.get_title_for_document(),
            "text": section_texts
        })
    return sections_str
    



def process_mail(run_mode: str, mail_key:str|None=None, pinecone_key:str|None=None, llm_key:str|None=None):
    date_today  = datetime.today()
    date_as_str = date_today.strftime("%d-%b-%Y")
    print("Processing for: {}".format(date_as_str))

    content = Explorer(date_as_str, mail_key).retrive_email()
    
    sections = Parser(content).parse_sections()
    
    print(f"{len(sections)} sections found")

    sections_for_export = _filter_sections_for_export(sections)
    
    if run_mode == "PROD":
        vector_store_documents = _construct_documents_from_sections(sections_for_export, date_today.strftime("%Y-%m-%d"))

        print(f"Will add {len(vector_store_documents)} document")
        exporter = Exporter(pinecone_key, llm_key)
        exporter.embed_documents(vector_store_documents)
        exporter.print_stats()

    output_content = _construct_output_file(sections_for_export)

    if run_mode == "LOCAL_TEST":
        with open("parsed_news.json", "w", encoding="utf-8") as jfile:
            json.dump(output_content, jfile, ensure_ascii=False, indent=4)

    return output_content

if __name__ == '__main__':
    process_mail("LOCAL_TEST")