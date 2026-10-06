"""Web has no local filesystem ownership, even when a desktop record is present."""
import pytest
from nfprogress.core.services.documents import ProjectDocumentService
from nfprogress.core.errors import ValidationError
SENTINEL='/Users/C18_SECRET_PATH/book-private.docx'

def record():
    return dict(project_id='P',stage_id=None,content={'type':'doc','content':[{'type':'paragraph','content':[{'type':'text','text':'Portable manuscript'}]}]},exists=True,docx_path=SENTINEL,source_id='SOURCE-ID-C18-LOCAL-ONLY',last_synced_hash='local-only-hash',raw_binding={'path':SENTINEL},sync_state='synced')

def test_web_document_view_excludes_all_raw_local_binding_state():
    service=ProjectDocumentService(None,None,allow_local_files=False)
    value=service._public(record())
    assert value['content']==record()['content'] and value['symbols']>0
    assert value['docx_path'] is None and value['sync_state']=='unlinked'
    assert SENTINEL not in str(value) and 'SOURCE-ID-C18-LOCAL-ONLY' not in str(value)
    assert 'raw_binding' not in value and value['last_synced_hash'] is None

def test_desktop_legacy_binding_is_retained_on_its_device():
    service=ProjectDocumentService(None,None,allow_local_files=True)
    assert service._public(record())['docx_path']==SENTINEL
    assert service._public(record())['raw_binding']==record()['raw_binding']

def test_web_external_actions_fail_before_any_repository_or_filesystem_access():
    service=ProjectDocumentService(None,None,allow_local_files=False)
    for action in [lambda:service.write_docx('P','invalid-base64'),lambda:service.read_external_docx('P'),lambda:service.accept_word('P',{},'hash')]:
        with pytest.raises(ValidationError,match='desktop'):action()
