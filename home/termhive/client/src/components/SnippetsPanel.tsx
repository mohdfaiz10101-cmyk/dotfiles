import { useEffect, useState } from 'react';
import Ic from './Icons';
import * as api from '../api';
import type { Agent, Snippet } from '../api';

interface Props {
  open: boolean;
  onClose: () => void;
  projectId: string | null;
  agent: Agent | null;
  send: (message: object) => void;
}

export default function SnippetsPanel({ open, onClose, projectId, agent, send }: Props) {
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [command, setCommand] = useState('');
  const [category, setCategory] = useState('');
  const [projectOnly, setProjectOnly] = useState(true);
  const [error, setError] = useState('');

  const load = () => api.listSnippets(projectId || undefined)
    .then(setSnippets)
    .catch((err) => setError(err instanceof Error ? err.message : String(err)));

  useEffect(() => {
    if (open) load();
  }, [open, projectId]);

  if (!open) return null;

  const run = (snippet: Snippet) => {
    if (!agent) { setError('Select a terminal first.'); return; }
    if (agent.status === 'stopped') { setError(`Start ${agent.name} before running a snippet.`); return; }
    send({ type: 'terminal:input', agentId: agent.id, data: snippet.command });
    send({ type: 'terminal:input', agentId: agent.id, data: '\r' });
    setError('');
    onClose();
  };

  const save = async () => {
    if (!name.trim() || !command.trim()) return;
    try {
      await api.createSnippet({
        name: name.trim(),
        command,
        category: category.trim() || undefined,
        projectId: projectOnly ? projectId || undefined : undefined,
      });
      setName(''); setCommand(''); setCategory(''); setEditing(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const remove = async (id: string) => {
    if (!confirm('Delete this snippet?')) return;
    await api.deleteSnippet(id);
    await load();
  };

  return (
    <div className="tools-scrim" onClick={onClose}>
      <section className="tools-drawer" onClick={(event) => event.stopPropagation()}>
        <header className="tools-head">
          <div>
            <h2>Snippets</h2>
            <p>{agent ? `Send commands to ${agent.name}` : 'Select a terminal to run commands'}</p>
          </div>
          <div className="tools-head-actions">
            <button className="hbtn" onClick={() => setEditing((value) => !value)}><Ic.plus size={13} /></button>
            <button className="hbtn" onClick={onClose}><Ic.x size={13} /></button>
          </div>
        </header>
        {editing && (
          <div className="snippet-editor">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name, e.g. System status" />
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="Category (optional)" />
            <textarea value={command} onChange={(e) => setCommand(e.target.value)} placeholder="Command" rows={4} />
            <label className="snippet-scope">
              <input type="checkbox" checked={projectOnly} onChange={(e) => setProjectOnly(e.target.checked)} />
              Only show in this project
            </label>
            <button className="batch-btn primary" onClick={save} disabled={!name.trim() || !command.trim()}>
              Save snippet
            </button>
          </div>
        )}
        {error && <div className="tools-error">{error}</div>}
        <div className="snippet-list scroll">
          {snippets.map((snippet) => (
            <div className="snippet-row" key={snippet.id}>
              <button className="snippet-run" onClick={() => run(snippet)}>
                <span className="snippet-icon"><Ic.terminal size={13} /></span>
                <span className="snippet-main">
                  <b>{snippet.name}</b>
                  <code>{snippet.command}</code>
                </span>
                {snippet.category && <span className="snippet-category">{snippet.category}</span>}
              </button>
              <button className="snippet-delete" onClick={() => remove(snippet.id)} title="Delete"><Ic.x size={11} /></button>
            </div>
          ))}
          {snippets.length === 0 && <div className="panel-empty">No snippets yet. Add your first reusable command.</div>}
        </div>
      </section>
    </div>
  );
}
