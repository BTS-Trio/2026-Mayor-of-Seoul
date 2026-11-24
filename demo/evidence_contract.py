"""Validate source identity without presenting synthetic documents as official."""
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent

def https(value):
    parsed=urlparse(value or '')
    return parsed.scheme=='https' and bool(parsed.netloc)

def valid_evidence(item,doc):
    if not doc:
        return False
    page=item.get('pdf_page')
    if (type(page) is not int or page<1 or page>doc.get('pdf_pages_verified',0)
        or item.get('citation')!=f'[{item["document_id"]}, PDF {page}쪽]'
        or item.get('candidate')!=doc.get('candidate')
        or item.get('candidate_id')!=doc.get('candidate_id')
        or item.get('candidate_withdrawn')!=doc.get('candidate_withdrawn')
        or item.get('source_id')!=doc.get('source_id')
        or item.get('data_kind')!=doc.get('data_kind')
        or not item.get('text') or not item.get('evidence_text')
        or item.get('stored_pdf_url')!=doc.get('stored_pdf_url')
        or item.get('rag_eligible') is not True):
        return False
    if item.get('data_kind')=='synthetic':
        did=item['document_id']
        expected=f'data/pdf/{did}.pdf'
        return (doc.get('local_document')==expected and (ROOT/expected).is_file()
            and item.get('stored_pdf_url')==f'/sources/{did}.pdf'
            and not item.get('official_pdf_download_url') and not item.get('source_site_url'))
    return item.get('data_kind')=='collected_real' and all(https(item.get(key)) for key in
        ('stored_pdf_url','official_pdf_download_url','source_site_url'))
