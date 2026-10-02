from types import SimpleNamespace
from tessera import cli
from tessera.presentation import CommandResult, OutputPolicy, human_lines

PAYLOAD={'persisted':True,'filepath':'project/note.md','admission':'accept',
    'write_receipt':{'operation_id':'write-1','repair_required':True,'errors':['index_update_failed']}}


def test_partial_write_renderer_keeps_completion_boundary_and_repair_hint():
    result=CommandResult('write',PAYLOAD,3)
    text='\n'.join(human_lines(result,OutputPolicy()))
    assert 'incomplete' in text and 'receipt repair --operation-id write-1' in text
    assert 'index_update_failed' in text


def test_write_command_preserves_partial_completion_exit(monkeypatch,capsys):
    result=SimpleNamespace(persisted=True,to_dict=lambda:PAYLOAD)
    engine=SimpleNamespace(write_memory_note_result=lambda **kw:result)
    monkeypatch.setattr(cli,'_engine_for_args',lambda args:engine)
    code=cli.main(['write','unused','--id','project/note','--type','factual',
        '--episode','ep','--content','A factual memory.','--json'])
    import json
    assert code==3
    assert json.loads(capsys.readouterr().out)==PAYLOAD
