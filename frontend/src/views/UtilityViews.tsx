import { useRef, useState } from 'react';
import { Activity, AlertTriangle, ArrowDownToLine, ArrowRight, Check, Database, FileArchive, FileJson2, FileSpreadsheet, HardDriveDownload, Info, Mail, RefreshCw, ShieldCheck, Trophy, Upload, Users } from 'lucide-react';
import type { Workspace } from '../types';
import { Dialog } from '../components/Dialog';

export function AboutView() {
  return <div className="page-content utility-page about-page">
    <section className="about-hero utility-card">
      <div className="about-mark" aria-hidden="true"><i /><i /><i /></div>
      <div><span className="eyebrow">TABLE TENNIS · CLUB OPERATIONS</span><h2>Rallydesk</h2><p>A calmer way to run club matches, organise tournaments, and understand the results.</p></div>
    </section>
    <div className="about-grid">
      <article className="utility-card about-card"><Users size={19} /><h3>Made for your club</h3><p>Start with an empty workspace, add the players you know, and name your club when you’re ready. Rallydesk doesn’t come with sample people or a prefilled club.</p></article>
      <article className="utility-card about-card"><Trophy size={19} /><h3>From a match to a full draw</h3><p>Create one-off matches or tournaments with generated draws, then keep scores and standings together as play progresses.</p></article>
      <article className="utility-card about-card"><Activity size={19} /><h3>Results you can review</h3><p>Player records and statistics are calculated from match results. Export tools help you keep a copy of the workspace data.</p></article>
      <article className="utility-card about-card"><Info size={19} /><h3>Preview status</h3><p>This version stores its workspace in this browser. Accounts, cloud synchronisation, and production privacy controls are part of the planned release work.</p></article>
    </div>
    <section className="utility-card about-support"><div><span className="eyebrow">NEED A HAND?</span><h3>Talk to the Rallydesk team</h3><p>Questions, feedback, or a problem to report? Send us a note.</p></div><a className="button button-primary" href="mailto:rallydesksupport@gmail.com"><Mail size={16} /> Email support <ArrowRight size={14} /></a></section>
  </div>;
}

export function ExportsView({ workspace, onToast }: { workspace: Workspace; onToast: (message: string) => void }) {
  const [busy, setBusy] = useState(false);
  const exportJson = () => {
    setBusy(true);
    window.setTimeout(() => { downloadFile(`rallydesk-workspace-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify({ schemaVersion: 1, exportedAt: new Date().toISOString(), source: 'Rallydesk local preview', workspace }, null, 2), 'application/json'); setBusy(false); onToast('Workspace JSON downloaded'); }, 180);
  };
  const exportPlayers = () => {
    const header = 'player_id,name,hand,grip,style,rating,wins,losses,points_won';
    const rows = workspace.players.map((player) => [player.id, player.name, player.hand, player.grip, player.style, player.rating, player.wins, player.losses, player.pointsWon].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','));
    downloadFile(`rallydesk-players-${new Date().toISOString().slice(0, 10)}.csv`, [header, ...rows].join('\n'), 'text/csv'); onToast('Player list downloaded');
  };
  const exportMatches = () => {
    const header = 'match_id,tournament,status,player_one,player_two,format,table,games_one,games_two';
    const rows = workspace.matches.map((match) => [match.id, match.tournamentName ?? '', match.status, workspace.players.find((p) => p.id === match.playerOneId)?.name ?? '', workspace.players.find((p) => p.id === match.playerTwoId)?.name ?? '', match.format, match.table ?? '', match.gamesWon[match.playerOneId] ?? 0, match.gamesWon[match.playerTwoId] ?? 0].map((value) => `"${String(value).replaceAll('"', '""')}"`).join(','));
    downloadFile(`rallydesk-matches-${new Date().toISOString().slice(0, 10)}.csv`, [header, ...rows].join('\n'), 'text/csv'); onToast('Match summary downloaded');
  };
  return <div className="page-content utility-page">
    <div className="page-intro"><div><p className="eyebrow">PORTABILITY & RECOVERY</p><h2>Your records, ready to move</h2><p>Export the preview workspace or download a spreadsheet-friendly summary.</p></div></div>
    <section className="export-primary"><div className="export-art"><FileArchive size={25} /><span>JSON<br />CSV</span></div><div className="export-copy"><p className="eyebrow">WORKSPACE EXPORT</p><h3>Take a copy of your club data</h3><p>Includes player profiles, match summaries, event timelines and tournament records. This preview export stays on your device.</p><div className="export-includes"><span><Check size={13} /> Players</span><span><Check size={13} /> Matches</span><span><Check size={13} /> Tournaments</span><span><Check size={13} /> Point timeline</span></div></div><button className="button button-primary" onClick={exportJson} disabled={busy}><ArrowDownToLine size={16} />{busy ? 'Preparing…' : 'Download workspace JSON'}</button></section>
    <div className="export-grid"><ExportTile icon={FileSpreadsheet} title="Player list" description={`${workspace.players.length} profiles · CSV format`} button="Download CSV" onClick={exportPlayers} /><ExportTile icon={FileSpreadsheet} title="Match summary" description={`${workspace.matches.length} matches · CSV format`} button="Download CSV" onClick={exportMatches} /><ExportTile icon={FileJson2} title="Tournament records" description={`${workspace.tournaments.length} events · JSON format`} button="Download JSON" onClick={() => downloadFile(`rallydesk-tournaments-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(workspace.tournaments, null, 2), 'application/json')} /></div>
    <div className="export-note"><Info size={15} /><span><b>Local preview limitation.</b> Downloads include only the records saved in this browser. No account or cloud copy is connected yet.</span></div>
    <section className="recovery-block"><div><p className="eyebrow">RECOVERY PLAN</p><h3>Keep a copy before event day</h3><p>Before a tournament, export a fresh copy and keep it somewhere you can reach if your device is unavailable.</p></div><div className="recovery-steps"><span><b>01</b> Download the workspace</span><ArrowRight size={14} /><span><b>02</b> Store a second copy</span><ArrowRight size={14} /><span><b>03</b> Check it opens</span></div></section>
  </div>;
}

function ExportTile({ icon: Icon, title, description, button, onClick }: { icon: typeof FileSpreadsheet; title: string; description: string; button: string; onClick: () => void }) {
  return <section className="export-tile"><span className="export-tile-icon"><Icon size={18} /></span><div><b>{title}</b><small>{description}</small></div><button className="text-action" onClick={onClick}>{button} <ArrowRight size={13} /></button></section>;
}

export function SettingsView({ workspace, clubName, onSaveClubName, onImportWorkspace, onReset }: { workspace: Workspace; clubName: string; onSaveClubName: (name: string) => void; onImportWorkspace: (workspace: Workspace) => void; onReset: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [confirmation, setConfirmation] = useState(false);
  const [clubDraft, setClubDraft] = useState(clubName);
  const [message, setMessage] = useState('');
  const [restoreCandidate, setRestoreCandidate] = useState<Workspace | null>(null);
  const handleImport = async (file?: File) => {
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as { workspace?: unknown };
      if (!isWorkspace(parsed.workspace)) throw new Error('That file does not contain a valid Rallydesk workspace backup.');
      setRestoreCandidate(parsed.workspace); setMessage('');
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not read that file.'); }
  };
  return <div className="page-content utility-page settings-page">
    <div className="page-intro"><div><p className="eyebrow">PREFERENCES</p><h2>Workspace settings</h2><p>Local preview preferences and data controls.</p></div></div>
    <section className="settings-panel"><div className="settings-panel-title"><div><p className="eyebrow">YOUR CLUB</p><h3>Club name</h3><p>This name appears in your workspace and event context. You can change it any time.</p></div></div><form className="settings-club-form" noValidate onSubmit={(event) => { event.preventDefault(); onSaveClubName(clubDraft.trim()); }}><label className="field"><span>Club or workspace name</span><input value={clubDraft} onChange={(event) => setClubDraft(event.target.value)} placeholder="Enter your club name" maxLength={80} /></label><button className="button button-primary" type="submit">Save name</button></form></section>
    <section className="settings-panel"><div className="settings-panel-title"><div><p className="eyebrow">STORAGE</p><h3>Local preview workspace</h3><p>Records are stored in this browser only. Sign-in and shared club storage will be added in the publishing phase.</p></div><span className="storage-status"><i /> DEVICE ONLY</span></div><div className="settings-data-row"><span className="settings-data-icon"><Database size={17} /></span><div><b>Browser storage</b><small>Data stays on this device · no account connected</small></div><span className="settings-data-count">Preview mode</span></div><div className="settings-buttons"><button className="button button-outline" onClick={() => fileRef.current?.click()}><Upload size={15} /> Restore from JSON</button><input ref={fileRef} className="sr-only" type="file" accept="application/json,.json" onChange={(event) => { handleImport(event.target.files?.[0]); event.target.value = ''; }} /><button className="button button-outline" onClick={() => { const text = JSON.stringify({ schemaVersion: 1, exportedAt: new Date().toISOString(), source: 'Rallydesk local preview', workspace }, null, 2); downloadFile('rallydesk-local-backup.json', text, 'application/json'); setMessage('Backup downloaded.'); }}><HardDriveDownload size={15} /> Download backup</button></div>{message && <div className="inline-message" role="status"><Info size={14} />{message}</div>}</section>
    <section className="settings-panel settings-panel--danger"><div className="settings-panel-title"><div><p className="eyebrow">WORKSPACE DATA</p><h3>Clear this workspace</h3><p>Remove the players, matches and tournaments saved in this browser.</p></div><span className="danger-mark"><AlertTriangle size={17} /></span></div>{!confirmation ? <button className="button button-danger-outline" onClick={() => setConfirmation(true)}><RefreshCw size={15} /> Clear workspace</button> : <div className="reset-confirm"><span><b>Clear all workspace records?</b><small>This cannot be undone unless you downloaded a backup.</small></span><button className="button button-quiet" onClick={() => setConfirmation(false)}>Cancel</button><button className="button button-danger" onClick={onReset}><RefreshCw size={14} /> Clear records</button></div>}</section>
    <div className="settings-footnote"><ShieldCheck size={16} /><span>Account security, consent records and shared database settings will be designed before public launch.</span></div>
    {restoreCandidate && <Dialog title="Restore this workspace?" eyebrow="REVIEW BACKUP" onClose={() => setRestoreCandidate(null)}><p className="dialog-copy">This will replace the records saved in this browser. Review the backup contents before continuing.</p><div className="restore-summary"><span><b>{restoreCandidate.players.length}</b><small>players</small></span><span><b>{restoreCandidate.matches.length}</b><small>matches</small></span><span><b>{restoreCandidate.tournaments.length}</b><small>tournaments</small></span></div><div className="dialog-actions"><button className="button button-quiet" onClick={() => setRestoreCandidate(null)}>Cancel</button><button className="button button-primary" onClick={() => { onImportWorkspace(restoreCandidate); setRestoreCandidate(null); setMessage('Backup restored to this browser.'); }}>Restore workspace</button></div></Dialog>}
  </div>;
}

function isWorkspace(value: unknown): value is Workspace {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<Workspace>;
  if (!Array.isArray(candidate.players) || !Array.isArray(candidate.matches) || !Array.isArray(candidate.tournaments)) return false;
  if (!candidate.players.every((player) => player && typeof player.id === 'string' && typeof player.name === 'string')) return false;
  if (!candidate.matches.every((match) => match && typeof match.id === 'string' && typeof match.playerOneId === 'string' && typeof match.playerTwoId === 'string' && Array.isArray(match.events) && match.gamesWon && match.score)) return false;
  return candidate.tournaments.every((tournament) => tournament && typeof tournament.id === 'string' && typeof tournament.name === 'string' && Array.isArray(tournament.entrantIds) && Array.isArray(tournament.matchIds) && Array.isArray(tournament.audit));
}

function downloadFile(name: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement('a'); link.href = url; link.download = name; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
