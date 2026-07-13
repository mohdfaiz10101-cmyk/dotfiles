import { useState } from 'react';

interface Flags {
  dangerouslySkipPermissions?: boolean;
  remoteControl?: boolean;
}

type TerminalType = 'claude' | 'codex' | 'gemini' | 'opencode' | 'shell' | 'ssh';

interface Props {
  projectCwd: string;
  initialCli?: TerminalType;
  onClose: () => void;
  onCreate: (data: {
    name: string;
    cli: TerminalType;
    cwd?: string;
    role?: string;
    flags?: Flags;
    connection?: {
      host?: string;
      user?: string;
      port?: number;
      identityFile?: string;
      startupCommand?: string;
    };
  }) => void;
}

export default function CreateAgentModal({ projectCwd, initialCli = 'shell', onClose, onCreate }: Props) {
  const [name, setName] = useState('');
  const [cli, setCli] = useState<TerminalType>(initialCli);
  const [cwd, setCwd] = useState(projectCwd);
  const [role, setRole] = useState('');
  const [skipPermissions, setSkipPermissions] = useState(false);
  const [remoteControl, setRemoteControl] = useState(false);
  const [host, setHost] = useState('');
  const [user, setUser] = useState('');
  const [port, setPort] = useState('22');
  const [identityFile, setIdentityFile] = useState('~/.ssh/id_ed25519');
  const [startupCommand, setStartupCommand] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;
    const flags: Flags = {};
    if (cli === 'claude' || cli === 'opencode') {
      if (skipPermissions) flags.dangerouslySkipPermissions = true;
    }
    if (cli === 'claude') {
      if (remoteControl) flags.remoteControl = true;
    }
    onCreate({
      name, cli,
      cwd: cwd || undefined,
      role: role || undefined,
      flags: Object.keys(flags).length > 0 ? flags : undefined,
      connection: cli === 'ssh' ? {
        host: host.trim(),
        user: user.trim(),
        port: Number(port) || 22,
        identityFile: identityFile.trim() || undefined,
        startupCommand: startupCommand.trim() || undefined,
      } : cli === 'shell' && startupCommand.trim() ? {
        startupCommand: startupCommand.trim(),
      } : undefined,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>{cli === 'ssh' ? 'New SSH Connection' : cli === 'shell' ? 'New Local Shell' : 'New Agent'}</h2>
        <form onSubmit={handleSubmit}>
          <label>Agent Name</label>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Frontend" autoFocus />

          <label>CLI</label>
          <select value={cli} onChange={e => setCli(e.target.value as TerminalType)}>
            <option value="shell">Local Shell</option>
            <option value="ssh">SSH Connection</option>
            <option value="claude">Claude Code</option>
            <option value="codex">Codex CLI</option>
            <option value="gemini">Gemini CLI</option>
            <option value="opencode">OpenCode</option>
          </select>

          {cli === 'ssh' && (
            <div className="connection-fields">
              <label>SSH Host</label>
              <input value={host} onChange={e => setHost(e.target.value)} placeholder="192.168.1.20 or server.example.com" />
              <div className="connection-row">
                <div>
                  <label>User</label>
                  <input value={user} onChange={e => setUser(e.target.value)} placeholder="charlie" />
                </div>
                <div>
                  <label>Port</label>
                  <input inputMode="numeric" value={port} onChange={e => setPort(e.target.value)} />
                </div>
              </div>
              <label>Identity File</label>
              <input value={identityFile} onChange={e => setIdentityFile(e.target.value)} placeholder="~/.ssh/id_ed25519" />
            </div>
          )}

          {(cli === 'shell' || cli === 'ssh') && (
            <>
              <label>Startup Command (optional)</label>
              <input
                value={startupCommand}
                onChange={e => setStartupCommand(e.target.value)}
                placeholder={cli === 'ssh' ? 'tmux new -As main' : 'tmux new -As local'}
              />
            </>
          )}

          {(cli === 'claude' || cli === 'opencode') && (
            <div style={{ marginTop: 12 }}>
              <label style={{ marginBottom: 8 }}>Flags</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', margin: 0 }}>
                  <input
                    type="checkbox"
                    checked={skipPermissions}
                    onChange={e => setSkipPermissions(e.target.checked)}
                    style={{ width: 'auto' }}
                  />
                  <span style={{ fontSize: 13 }}>--dangerously-skip-permissions</span>
                </label>
                {cli === 'claude' && (
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', margin: 0 }}>
                    <input
                      type="checkbox"
                      checked={remoteControl}
                      onChange={e => setRemoteControl(e.target.checked)}
                      style={{ width: 'auto' }}
                    />
                    <span style={{ fontSize: 13 }}>--remote-control</span>
                  </label>
                )}
              </div>
            </div>
          )}

          <label>Working Directory</label>
          <input value={cwd} onChange={e => setCwd(e.target.value)} />

          <label>Role (optional)</label>
          <input value={role} onChange={e => setRole(e.target.value)} placeholder="e.g. Frontend Developer" />

          <div className="modal-actions">
            <button type="button" onClick={onClose}>Cancel</button>
            <button
              type="submit"
              className="primary"
              disabled={!name || (cli === 'ssh' && (!host.trim() || !user.trim()))}
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
