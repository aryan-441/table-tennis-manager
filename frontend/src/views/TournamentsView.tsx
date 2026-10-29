import { useMemo, useRef, useState } from 'react';
import { Activity, AlertTriangle, ArrowRight, CalendarClock, CalendarDays, Check, ChevronRight, CircleHelp, Download, FileJson2, FileSpreadsheet, Pause, Play, Plus, ShieldCheck, Trophy, Undo2, Users } from 'lucide-react';
import type { Match, Player, Tournament, Workspace } from '../types';
import { Dialog } from '../components/Dialog';
import { StatusPill } from './MatchCenter';
import { createMatch, createTournament, generateKnockoutRoundFixtures, generateTournamentFixtures } from '../services/store';

type Props = { workspace: Workspace; players: Map<string, Player>; selectedId: string | null; onSelect: (id: string | null) => void; onCreate: () => void; onOpenMatch: (id: string) => void; onChange: (next: Workspace) => void; toast: (message: string) => void };
type TournamentTab = 'Overview' | 'Draw & matches' | 'Standings' | 'Audit log';
type ImportRow = { rowNumber: number; sourceId: string; playerOneId: string; playerTwoId: string; round: string; table: string; startsAt: string; oneMatch: string; twoMatch: string };
type ImportPreview = { fileName: string; rows: ImportRow[] };

export function TournamentsView({ workspace, players, selectedId, onSelect, onCreate, onOpenMatch, onChange, toast }: Props) {
  const selected = workspace.tournaments.find((item) => item.id === selectedId);
  const [tab, setTab] = useState<TournamentTab>('Overview');
  const [reasonAction, setReasonAction] = useState<'pause' | 'resume' | null>(null);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [scheduleEdit, setScheduleEdit] = useState<Match | null>(null);
  const [fieldEditOpen, setFieldEditOpen] = useState(false);
  const sorted = useMemo(() => [...workspace.tournaments].sort((a, b) => statusRank(a.status) - statusRank(b.status)), [workspace.tournaments]);
  const update = (next: Tournament) => onChange({ ...workspace, tournaments: workspace.tournaments.map((item) => item.id === next.id ? next : item) });
  const importDraw = async (file?: File) => {
    if (!selected || !file) return;
    try {
      const contents = await file.text();
      const rows = file.name.toLowerCase().endsWith('.json')
        ? (() => { const data = JSON.parse(contents); return Array.isArray(data) ? data : data.matches ?? data.workspace?.matches; })()
        : parseDrawCsv(contents);
      if (!Array.isArray(rows)) throw new Error('Choose a CSV or JSON file containing match rows.');
      if (!rows.length) throw new Error('The file has no match rows to review.');
      const entrantPlayers = selected.entrantIds.map((id) => players.get(id)).filter((player): player is Player => Boolean(player));
      const matchEntrant = (value: string) => {
        const normalized = value.trim().toLocaleLowerCase();
        const exactId = entrantPlayers.find((player) => player.id.toLocaleLowerCase() === normalized);
        const exactNames = entrantPlayers.filter((player) => player.name.trim().toLocaleLowerCase() === normalized);
        return { playerId: exactId?.id ?? (exactNames.length === 1 ? exactNames[0].id : ''), match: exactId ? 'id' : exactNames.length === 1 ? 'name' : exactNames.length > 1 ? 'ambiguous' : 'missing' };
      };
      const mappedRows: ImportRow[] = rows.map((raw, index) => {
        if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error(`Row ${index + 2} must be an object with player_one, player_two, and round fields.`);
        const row = Object.fromEntries(Object.entries(raw as Record<string, unknown>).map(([key, value]) => [key.toLowerCase().replace(/[^a-z0-9]/g, ''), String(value ?? '').trim()]));
        const firstRaw = row.playerone ?? row.playeronename ?? row.playeroneid ?? row.player1 ?? row.player1name ?? row.playera ?? row.home ?? '';
        const secondRaw = row.playertwo ?? row.playertwoname ?? row.playertwoid ?? row.player2 ?? row.player2name ?? row.playerb ?? row.away ?? '';
        const first = matchEntrant(firstRaw); const second = matchEntrant(secondRaw);
        return {
          rowNumber: index + 2,
          sourceId: row.matchid || row.id || '',
          playerOneId: first.playerId,
          playerTwoId: second.playerId,
          round: row.round || row.roundname || '',
          table: row.table || '',
          startsAt: row.starttime || row.startsat || row.time || 'TBD',
          oneMatch: first.match,
          twoMatch: second.match,
        };
      });
      setImportPreview({ fileName: file.name, rows: mappedRows });
    } catch (error) { toast(error instanceof Error ? error.message : 'Could not read that draw file'); }
  };
  const importErrors = useMemo(() => importPreview && selected ? validateImportPreview(importPreview.rows, selected, workspace, players) : [], [importPreview, selected, workspace, players]);
  const applyImport = () => {
    if (!selected || !importPreview || importErrors.length) return;
    const imported = importPreview.rows.map((row) => {
      const match = createMatch({ playerOneId: row.playerOneId, playerTwoId: row.playerTwoId, format: 'Best of 5', pointsPerGame: 11, gamesToWin: 3, tournamentId: selected.id, table: row.table || undefined }, workspace.players);
      match.tournamentName = selected.name; match.round = row.round.trim(); match.startsAt = row.startsAt.trim() || 'TBD';
      return match;
    });
    const audit = { id: crypto.randomUUID(), action: 'Draw imported', target: `${imported.length} fixtures`, reason: `Imported from ${importPreview.fileName}`, at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    const updatedTournament = { ...selected, matchIds: [...selected.matchIds, ...imported.map((match) => match.id)], audit: [audit, ...selected.audit] };
    onChange({ ...workspace, matches: [...imported, ...workspace.matches], tournaments: workspace.tournaments.map((item) => item.id === selected.id ? updatedTournament : item) });
    setImportPreview(null); toast(`${imported.length} draw ${imported.length === 1 ? 'match' : 'matches'} imported`);
  };
  const saveSchedule = (startsAt: string, table: string, reason: string) => {
    if (!scheduleEdit || !selected || scheduleEdit.status === 'Completed') return;
    const updatedMatch = { ...scheduleEdit, startsAt: startsAt.trim() || 'TBD', table: table.trim() || undefined };
    const audit = { id: crypto.randomUUID(), action: 'Match rescheduled', target: `${players.get(scheduleEdit.playerOneId)?.name ?? 'Player one'} vs ${players.get(scheduleEdit.playerTwoId)?.name ?? 'Player two'}`, reason, at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    onChange({ ...workspace, matches: workspace.matches.map((match) => match.id === updatedMatch.id ? updatedMatch : match), tournaments: workspace.tournaments.map((item) => item.id === selected.id ? { ...item, audit: [audit, ...item.audit] } : item) });
    setScheduleEdit(null); toast('Match schedule updated and recorded');
  };
  const selectedMatches = selected ? workspace.matches.filter((match) => match.tournamentId === selected.id || selected.matchIds.includes(match.id)) : [];
  const canEditField = Boolean(selected && selected.status === 'Upcoming' && selectedMatches.every((match) => match.status === 'Scheduled' && !match.winnerId && !match.events.length && !match.gameResults?.length));
  const saveField = (entrantIds: string[], reason: string) => {
    if (!selected || !canEditField || entrantIds.length < 2 || new Set(entrantIds).size !== entrantIds.length || entrantIds.some((id) => !workspace.players.some((player) => player.id === id))) return;
    const rebuilt = createTournament({ name: selected.name, format: selected.format, date: selected.date, venue: selected.venue, entrantIds });
    const fixtures = generateTournamentFixtures(rebuilt, workspace.players).map((match) => ({ ...match, tournamentId: selected.id, tournamentName: selected.name }));
    const oldIds = new Set(selectedMatches.map((match) => match.id));
    const audit = { id: crypto.randomUUID(), action: 'Entrants and draw updated', target: `${selected.entrantIds.length} → ${entrantIds.length} entrants · ${oldIds.size} pending fixtures replaced`, reason, at: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    const updatedTournament: Tournament = { ...selected, entrantIds, byePlayerIds: rebuilt.byePlayerIds, rounds: rebuilt.rounds, matchIds: fixtures.map((match) => match.id), completed: 0, status: 'Upcoming', standings: rebuilt.standings, audit: [audit, ...selected.audit] };
    onChange({ ...workspace, matches: [...fixtures, ...workspace.matches.filter((match) => !oldIds.has(match.id))], tournaments: workspace.tournaments.map((item) => item.id === selected.id ? updatedTournament : item) });
    setFieldEditOpen(false); toast('Entrants and pending draw updated and recorded');
  };
  const commitProgression = (reason: string) => {
    if (!selected || !reasonAction) return;
    const paused = reasonAction === 'pause';
    const at = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const audit = { id: crypto.randomUUID(), action: paused ? 'Progression paused' : 'Progression resumed', target: 'Tournament', reason, at };
    if (paused) update({ ...selected, progressPaused: true, status: 'Paused', audit: [audit, ...selected.audit] });
    else {
      let matches = workspace.matches;
      let matchIds = selected.matchIds;
      let auditEntries = [audit, ...selected.audit];
      const eventMatches = workspace.matches.filter((match) => match.tournamentId === selected.id || selected.matchIds.includes(match.id));
      const completed = eventMatches.filter((match) => match.status === 'Completed' && match.winnerId);
      const currentRound = Math.max(0, ...eventMatches.map((match) => Number(match.round?.match(/Round\s+(\d+)/i)?.[1] ?? 0)));
      const finalRoundComplete = eventMatches.length > 0 && completed.length === eventMatches.length && currentRound >= selected.rounds;
      let generatedCount = 0;
      if (selected.format === 'Knockout' && !finalRoundComplete && currentRound > 0 && currentRound < selected.rounds) {
        const roundMatches = eventMatches.filter((match) => match.round === `Round ${currentRound}`);
        const hasNextRound = eventMatches.some((match) => match.round === `Round ${currentRound + 1}`);
        if (roundMatches.length && roundMatches.every((match) => match.status === 'Completed' && match.winnerId) && !hasNextRound) {
          const qualifiers = [...(currentRound === 1 ? selected.byePlayerIds ?? [] : []), ...roundMatches.map((match) => match.winnerId!)].sort((one, two) => selected.entrantIds.indexOf(one) - selected.entrantIds.indexOf(two));
          const fixtures = generateKnockoutRoundFixtures(selected, qualifiers, currentRound + 1);
          matches = [...fixtures, ...matches]; matchIds = [...selected.matchIds, ...fixtures.map((match) => match.id)]; generatedCount = fixtures.length;
          const roundAudit = { id: crypto.randomUUID(), action: 'Knockout round generated', target: `Round ${currentRound + 1} · ${fixtures.length} fixtures`, reason: 'Completed round advanced after progression resumed', at };
          auditEntries = [roundAudit, ...auditEntries];
        }
      }
      const hasStarted = eventMatches.some((match) => match.status !== 'Scheduled' || match.events.length > 0);
      const status = finalRoundComplete ? 'Completed' : hasStarted ? 'Running' : 'Upcoming';
      onChange({ ...workspace, matches, tournaments: workspace.tournaments.map((item) => item.id === selected.id ? { ...selected, matchIds, progressPaused: false, status, audit: auditEntries } : item) });
      setReasonAction(null); toast(generatedCount ? `Progression resumed · ${generatedCount} next-round ${generatedCount === 1 ? 'fixture' : 'fixtures'} created` : 'Automatic progression resumed');
      return;
    }
    setReasonAction(null); toast('Automatic progression paused');
  };
  return <div className="page-content tournaments-page">
    {!selected ? <>
      <div className="page-intro"><div><p className="eyebrow">EVENT CONTROL</p><h2>Tournaments</h2><p>Plan a draw, follow the day and keep organiser decisions visible.</p></div><button className="button button-primary" onClick={onCreate}><Plus size={16} /> Create tournament</button></div>
      <div className="tournament-summary-line"><span><i className="summary-live-dot" />{workspace.tournaments.filter((item) => item.status === 'Running').length} running</span><span>{workspace.tournaments.filter((item) => item.status === 'Upcoming').length} upcoming</span><span>{workspace.tournaments.filter((item) => item.status === 'Completed').length} completed</span></div>
      <div className="tournament-list">{sorted.map((tournament) => <button className="tournament-row" key={tournament.id} onClick={() => { onSelect(tournament.id); setTab('Overview'); }}><span className={`tournament-emblem tournament-emblem--${tournament.format === 'Knockout' ? 'knockout' : 'round'}`}><Trophy size={19} /></span><span className="tournament-row-main"><span><b>{tournament.name}</b><span className="format-tag">{tournament.format}</span></span><small>{tournament.venue} <i>·</i> {tournament.date}</small></span><span className="tournament-row-entrants"><Users size={15} />{tournament.entrantIds.length} entrants</span><span className="tournament-progress-col"><b>{tournament.completed}<small> / {tournament.matchIds.length || tournament.rounds}</small></b><span className="mini-progress"><i style={{ width: `${Math.min(100, tournament.matchIds.length ? tournament.completed / tournament.matchIds.length * 100 : 0)}%` }} /></span><small>{tournament.matchIds.length ? 'matches complete' : 'rounds'}</small></span><TournamentStatus status={tournament.status} /><span className="row-open"><ArrowRight size={16} /></span></button>)}</div>
      {!workspace.tournaments.length && <div className="table-empty"><span className="empty-mark"><Trophy size={20} /></span><h3>No tournaments yet</h3><p>Create a tournament to start managing entrants, rounds and results.</p><button className="button button-primary" onClick={onCreate}>Create tournament <ArrowRight size={15} /></button></div>}
      <div className="organiser-note"><ShieldCheck size={17} /><span><b>Organiser control stays with you.</b> Draws can be changed, progression paused and results corrected with a reason kept in the audit history.</span></div>
    </> : <>
      <div className="tournament-detail-top"><button className="back-link" onClick={() => onSelect(null)}><Undo2 size={14} /> All tournaments</button><div className="detail-actions"><button className="button button-outline" onClick={() => exportTournamentPackage(selected, workspace, players)}><Download size={15} /> Export package</button><button className="button button-outline" onClick={() => setReasonAction(selected.progressPaused ? 'resume' : 'pause')}>{selected.progressPaused ? <Play size={15} /> : <Pause size={15} />}{selected.progressPaused ? 'Resume progression' : 'Pause progression'}</button><button className="button button-primary" onClick={() => { const nextMatch = selected.matchIds.map((id) => workspace.matches.find((match) => match.id === id)).filter((match): match is Match => Boolean(match && match.status !== 'Completed')).sort((a, b) => a.startsAt.localeCompare(b.startsAt))[0]; if (nextMatch) onOpenMatch(nextMatch.id); else toast('No playable match is scheduled yet'); }}><CircleHelp size={15} /> Open next match</button></div></div>
      <section className="tournament-detail-hero"><div className="detail-emblem"><Trophy size={22} /></div><div className="detail-title"><div className="detail-title-top"><TournamentStatus status={selected.status} /><span className="format-tag">{selected.format}</span><span className="detail-created">Created {selected.date}</span></div><h2>{selected.name}</h2><p><CalendarDays size={14} /> {selected.date}<i /> <Users size={14} /> {selected.entrantIds.length} entrants<i />{selected.venue}</p></div><div className="detail-progress"><span>EVENT PROGRESS</span><b>{selected.completed}<small> / {selected.matchIds.length || selected.rounds}</small></b><div className="mini-progress"><i style={{ width: `${selected.matchIds.length ? Math.min(100, selected.completed / selected.matchIds.length * 100) : 0}%` }} /></div><small>{selected.matchIds.length ? 'matches complete' : 'rounds to play'}</small></div></section>
      <div className="tournament-tabs" role="tablist" aria-label="Tournament sections">{(['Overview', 'Draw & matches', 'Standings', 'Audit log'] as TournamentTab[]).map((item) => <button key={item} role="tab" aria-selected={tab === item} className={tab === item ? 'tournament-tab tournament-tab--active' : 'tournament-tab'} onClick={() => setTab(item)}>{item}{item === 'Audit log' && <span>{selected.audit.length}</span>}</button>)}</div>
      {tab === 'Overview' && <TournamentOverview tournament={selected} matches={selectedMatches} players={players} onOpenMatch={onOpenMatch} onTab={setTab} onEditField={() => setFieldEditOpen(true)} canEditField={canEditField} />}
      {tab === 'Draw & matches' && <TournamentDraw tournament={selected} matches={workspace.matches.filter((match) => match.tournamentId === selected.id || selected.matchIds.includes(match.id))} players={players} onOpenMatch={onOpenMatch} onImport={importDraw} onReschedule={setScheduleEdit} />}
      {tab === 'Standings' && <TournamentStandings tournament={selected} players={players} matches={workspace.matches.filter((match) => match.tournamentId === selected.id || selected.matchIds.includes(match.id))} />}
      {tab === 'Audit log' && <TournamentAudit tournament={selected} />}
    </>}
    {importPreview && selected && <ImportDrawDialog preview={importPreview} entrants={selected.entrantIds.map((id) => players.get(id)).filter((player): player is Player => Boolean(player))} errors={importErrors} onChange={(rowIndex, key, playerId) => setImportPreview((current) => current ? { ...current, rows: current.rows.map((row, index) => index === rowIndex ? { ...row, [key]: playerId, ...(key === 'playerOneId' ? { oneMatch: 'manual' } : { twoMatch: 'manual' }) } : row) } : current)} onClose={() => setImportPreview(null)} onApply={applyImport} />}
    {scheduleEdit && <ScheduleDialog match={scheduleEdit} onClose={() => setScheduleEdit(null)} onSave={saveSchedule} />}
    {fieldEditOpen && selected && <EditFieldDialog tournament={selected} players={workspace.players} pendingFixtureCount={selectedMatches.length} onClose={() => setFieldEditOpen(false)} onSave={saveField} />}
    {reasonAction && <ReasonDialog action={reasonAction} onClose={() => setReasonAction(null)} onConfirm={commitProgression} />}
  </div>;
}

function TournamentOverview({ tournament, matches, players, onOpenMatch, onTab, onEditField, canEditField }: { tournament: Tournament; matches: Match[]; players: Map<string, Player>; onOpenMatch: (id: string) => void; onTab: (tab: TournamentTab) => void; onEditField: () => void; canEditField: boolean }) {
  const nextMatches = [...matches].sort((a, b) => a.startsAt.localeCompare(b.startsAt)).slice(0, 4);
  return <div className="tournament-overview-grid"><section className="tournament-section"><div className="section-head"><div><p className="eyebrow">ON THE TABLE</p><h3>Next matches</h3></div><button className="quiet-link" onClick={() => onTab('Draw & matches')}>Full draw <ArrowRight size={14} /></button></div>{nextMatches.length ? <div className="tournament-match-list">{nextMatches.map((match) => <TournamentMatchRow key={match.id} match={match} players={players} onClick={() => onOpenMatch(match.id)} />)}</div> : <div className="empty-draw"><span className="empty-mark"><Activity size={18} /></span><div><b>No fixtures yet</b><span>Add a draw or create a match for this event.</span></div></div>}</section>
    <section className="tournament-section control-section"><div className="section-head"><div><p className="eyebrow">ORGANISER CONTROL</p><h3>Event settings</h3></div><span className="settings-symbol"><Activity size={15} /></span></div><div className="setting-line"><span>Format</span><b>{tournament.format}</b></div><div className="setting-line"><span>Automatic progression</span><b className={tournament.progressPaused ? 'state-off' : 'state-on'}><i />{tournament.progressPaused ? 'Paused' : 'Available'}</b></div><div className="setting-line"><span>Entrants</span><b>{tournament.entrantIds.length} players</b></div>{tournament.tieBreaks.length > 0 && <div className="tie-break-box"><span>STANDINGS ORDER</span><p>{tournament.tieBreaks.join(' < ')} <ChevronRight size={13} /></p></div>}<button className="control-audit-link" onClick={() => onTab('Audit log')}>Review change history <ArrowRight size={14} /></button></section>
    <section className="entrant-strip"><div><p className="eyebrow">THE FIELD</p><h3>{tournament.entrantIds.length} entrants</h3><small className="field-edit-hint">{canEditField ? 'Pending draw can be safely rebuilt' : 'Field locks when a match starts'}</small></div><div className="entrant-avatars">{tournament.entrantIds.slice(0, 6).map((id) => <span className="avatar avatar--tiny" key={id}>{players.get(id)?.initials ?? '?'}</span>)}{tournament.entrantIds.length > 6 && <span className="avatar avatar--tiny entrant-more">+{tournament.entrantIds.length - 6}</span>}</div><span className="entrant-strip-spacer" /><button className="button button-outline field-edit-button" onClick={onEditField} disabled={!canEditField}>Edit entrants</button><button className="quiet-link" onClick={() => onTab('Standings')}>Standings <ArrowRight size={14} /></button></section>
  </div>;
}

function TournamentDraw({ tournament, matches, players, onOpenMatch, onImport, onReschedule }: { tournament: Tournament; matches: Match[]; players: Map<string, Player>; onOpenMatch: (id: string) => void; onImport: (file?: File) => void; onReschedule: (match: Match) => void }) {
  const [roundFilter, setRoundFilter] = useState('All rounds');
  const importRef = useRef<HTMLInputElement>(null);
  const rounds = [...new Set(matches.map((match) => match.round ?? 'Unassigned'))];
  const filtered = matches.filter((match) => roundFilter === 'All rounds' || match.round === roundFilter);
  const grouped = filtered.reduce<Record<string, Match[]>>((groups, match) => { const key = match.round ?? 'Unassigned'; (groups[key] ??= []).push(match); return groups; }, {});
  return <section className="tournament-section draw-section"><div className="section-head"><div><p className="eyebrow">DRAW CONTROL</p><h3>Draw & matches</h3><p className="section-caption">Review each fixture. Open a match to score, reschedule or record a result.</p></div><div className="draw-toolbar"><select value={roundFilter} onChange={(event) => setRoundFilter(event.target.value)} aria-label="Filter by round"><option>All rounds</option>{rounds.map((round) => <option key={round}>{round}</option>)}</select><button className="button button-outline template-button" onClick={() => downloadDrawTemplate('csv')}><FileSpreadsheet size={14} /><span>CSV template</span></button><button className="button button-outline template-button" onClick={() => downloadDrawTemplate('json')}><FileJson2 size={14} /><span>JSON template</span></button><button className="button button-outline" onClick={() => importRef.current?.click()}><Plus size={15} /> Import draw</button><input ref={importRef} type="file" className="sr-only" accept=".csv,.json,text/csv,application/json" onChange={(event) => { onImport(event.target.files?.[0]); event.target.value = ''; }} /></div></div>
    {Object.keys(grouped).length ? <div className="draw-groups">{Object.entries(grouped).map(([round, items]) => <div className="draw-group" key={round}><div className="draw-group-title"><span>{round}</span><i /><small>{items.length} matches</small></div>{items.map((match) => <div className="tournament-match-shell" key={match.id}><TournamentMatchRow match={match} players={players} onClick={() => onOpenMatch(match.id)} expanded /><button className="reschedule-button" onClick={() => onReschedule(match)} disabled={match.status === 'Completed'} aria-label={`Reschedule ${players.get(match.playerOneId)?.name} versus ${players.get(match.playerTwoId)?.name}`}><CalendarClock size={14} /><span>Reschedule</span></button></div>)}</div>)}</div> : tournament.format === 'Knockout' ? <KnockoutPreview tournament={tournament} players={players} /> : <div className="empty-draw"><span className="empty-mark"><Trophy size={18} /></span><div><b>No matches in this draw</b><span>Import a CSV or JSON draw, or add matches to the event.</span></div><button className="button button-outline" onClick={() => importRef.current?.click()}><Plus size={14} /> Import draw</button></div>}
  </section>;
}

function ImportDrawDialog({ preview, entrants, errors, onChange, onClose, onApply }: { preview: ImportPreview; entrants: Player[]; errors: string[]; onChange: (rowIndex: number, key: 'playerOneId' | 'playerTwoId', playerId: string) => void; onClose: () => void; onApply: () => void }) {
  return <Dialog title="Review imported draw" eyebrow="NON-DESTRUCTIVE PREVIEW" onClose={onClose} size="wide">
    <div className="import-review-summary"><FileSpreadsheet size={17} /><span><b>{preview.fileName}</b><small>{preview.rows.length} fixtures found · nothing has been added yet</small></span></div>
    {errors.length > 0 && <div className="import-review-errors" role="alert"><AlertTriangle size={16} /><div><b>Resolve these issues before importing</b><ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div></div>}
    <p className="table-scroll-hint"><ArrowRight size={13} /> Swipe or use arrow keys to review all fields</p>
    <div className="import-review-table-wrap" role="region" aria-label="Scrollable imported draw preview" tabIndex={0}><table className="data-table import-review-table"><thead><tr><th>ROW</th><th>PLAYER ONE</th><th></th><th>PLAYER TWO</th><th>ROUND</th><th>TABLE</th></tr></thead><tbody>{preview.rows.map((row, index) => <tr key={row.rowNumber}><td>{row.rowNumber}</td><td><label className="sr-only" htmlFor={`import-one-${row.rowNumber}`}>Player one for row {row.rowNumber}</label><select id={`import-one-${row.rowNumber}`} value={row.playerOneId} onChange={(event) => onChange(index, 'playerOneId', event.target.value)}><option value="">{row.oneMatch === 'ambiguous' ? 'Choose matching name' : 'Map to roster player'}</option>{entrants.map((player) => <option key={player.id} value={player.id}>{player.name} · {player.id.slice(0, 6)}</option>)}</select></td><td>vs</td><td><label className="sr-only" htmlFor={`import-two-${row.rowNumber}`}>Player two for row {row.rowNumber}</label><select id={`import-two-${row.rowNumber}`} value={row.playerTwoId} onChange={(event) => onChange(index, 'playerTwoId', event.target.value)}><option value="">{row.twoMatch === 'ambiguous' ? 'Choose matching name' : 'Map to roster player'}</option>{entrants.map((player) => <option key={player.id} value={player.id}>{player.name} · {player.id.slice(0, 6)}</option>)}</select></td><td>{row.round || <span className="import-missing">Missing</span>}</td><td>{row.table || '—'}</td></tr>)}</tbody></table></div>
    <p className="import-review-note">Fixtures are appended to this tournament. Existing matches and results are kept. Duplicate fixtures and multiple fixtures per player in one round are blocked.</p>
    <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel import</button><button className="button button-primary" type="button" onClick={onApply} disabled={errors.length > 0}><Check size={15} /> Import {preview.rows.length} fixtures</button></div>
  </Dialog>;
}

function ScheduleDialog({ match, onClose, onSave }: { match: Match; onClose: () => void; onSave: (startsAt: string, table: string, reason: string) => void }) {
  const [startsAt, setStartsAt] = useState(match.startsAt === 'TBD' ? '' : match.startsAt);
  const [table, setTable] = useState(match.table ?? '');
  const [reason, setReason] = useState('');
  return <Dialog title="Reschedule match" eyebrow="ORGANISER CHANGE" onClose={onClose}>
    <form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (reason.trim()) onSave(startsAt, table, reason.trim()); }}>
      <p className="dialog-copy">Change the start time or table. Your reason will be kept in this tournament’s audit log.</p>
      <label className="field"><span>Start time</span><input autoFocus value={startsAt} onChange={(event) => setStartsAt(event.target.value)} placeholder="e.g. 10:30 or TBD" maxLength={40} /></label>
      <label className="field"><span>Table</span><input value={table} onChange={(event) => setTable(event.target.value)} placeholder="Leave blank to unassign" maxLength={40} /></label>
      <label className="field"><span>Reason for this change</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="e.g. Table became unavailable" maxLength={160} required /></label>
      <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={!reason.trim()}><CalendarClock size={15} /> Save schedule</button></div>
    </form>
  </Dialog>;
}

function EditFieldDialog({ tournament, players, pendingFixtureCount, onClose, onSave }: { tournament: Tournament; players: Player[]; pendingFixtureCount: number; onClose: () => void; onSave: (entrantIds: string[], reason: string) => void }) {
  const [entrantIds, setEntrantIds] = useState(tournament.entrantIds);
  const [reason, setReason] = useState('');
  const toggle = (id: string) => setEntrantIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  return <Dialog title="Edit tournament entrants" eyebrow="SAFE DRAW CHANGE" onClose={onClose} size="wide">
    <form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (entrantIds.length >= 2 && reason.trim()) onSave(entrantIds, reason.trim()); }}>
      <p className="dialog-copy">This event has not started. Changing the field rebuilds its pending {tournament.format.toLowerCase()} draw. No match results will be removed.</p>
      <div className="field-edit-count"><Users size={16} /><span><b>{entrantIds.length} entrants selected</b><small>{pendingFixtureCount} pending {pendingFixtureCount === 1 ? 'fixture' : 'fixtures'} will be replaced</small></span></div>
      <div className="entrant-picker"><div className="entrant-picker-head"><span>Choose the field</span><small>At least 2 players</small></div><div className="entrant-list">{players.map((player) => <label className={`entrant-option ${entrantIds.includes(player.id) ? 'entrant-option--selected' : ''}`} key={player.id}><input type="checkbox" checked={entrantIds.includes(player.id)} onChange={() => toggle(player.id)} /><span className="avatar avatar--tiny">{player.initials}</span><span>{player.name}</span><span className="entrant-rating">{player.rating}</span></label>)}</div></div>
      <label className="field"><span>Reason for this change</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="e.g. A player can no longer attend" required maxLength={160} /></label>
      <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={entrantIds.length < 2 || !reason.trim()}><Users size={15} /> Rebuild pending draw</button></div>
    </form>
  </Dialog>;
}

function exportTournamentPackage(tournament: Tournament, workspace: Workspace, players: Map<string, Player>) {
  const matches = workspace.matches.filter((match) => match.tournamentId === tournament.id || tournament.matchIds.includes(match.id));
  const packageData = { schemaVersion: 1, exportedAt: new Date().toISOString(), source: 'Rallydesk local preview', tournament, entrants: tournament.entrantIds.map((id) => players.get(id)).filter(Boolean), matches };
  const url = URL.createObjectURL(new Blob([JSON.stringify(packageData, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `rallydesk-${slug(tournament.name)}-tournament.json`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function slug(value: string) { return value.trim().toLocaleLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'event'; }

function validateImportPreview(rows: ImportRow[], tournament: Tournament, workspace: Workspace, players: Map<string, Player>): string[] {
  const errors: string[] = []; const entrants = new Set(tournament.entrantIds); const sourceIds = new Set<string>();
  const pairs = new Set<string>(); const playedByRound = new Set<string>();
  const existing = workspace.matches.filter((match) => match.tournamentId === tournament.id || tournament.matchIds.includes(match.id));
  for (const row of rows) {
    const round = row.round.trim();
    if (row.sourceId) {
      if (sourceIds.has(row.sourceId)) errors.push(`Row ${row.rowNumber}: source match ID ${row.sourceId} is duplicated in this file.`);
      else sourceIds.add(row.sourceId);
      if (workspace.matches.some((match) => match.id === row.sourceId)) errors.push(`Row ${row.rowNumber}: source match ID ${row.sourceId} already exists in this workspace.`);
    }
    if (!row.playerOneId) errors.push(`Row ${row.rowNumber}: map player one to a roster player (${row.oneMatch === 'ambiguous' ? 'the name is duplicated' : 'no exact roster match was found'}).`);
    if (!row.playerTwoId) errors.push(`Row ${row.rowNumber}: map player two to a roster player (${row.twoMatch === 'ambiguous' ? 'the name is duplicated' : 'no exact roster match was found'}).`);
    if (row.playerOneId && !entrants.has(row.playerOneId)) errors.push(`Row ${row.rowNumber}: player one is not a tournament entrant.`);
    if (row.playerTwoId && !entrants.has(row.playerTwoId)) errors.push(`Row ${row.rowNumber}: player two is not a tournament entrant.`);
    if (row.playerOneId && row.playerOneId === row.playerTwoId) errors.push(`Row ${row.rowNumber}: choose two different players.`);
    if (!round) errors.push(`Row ${row.rowNumber}: add a round name.`);
    if (!round || !row.playerOneId || !row.playerTwoId || row.playerOneId === row.playerTwoId) continue;
    const pair = [row.playerOneId, row.playerTwoId].sort().join('|'); const pairKey = `${round.toLocaleLowerCase()}|${pair}`;
    if (pairs.has(pairKey)) errors.push(`Round ${round}: the same fixture appears more than once in this file.`);
    pairs.add(pairKey);
    if (existing.some((match) => (match.round ?? '').toLocaleLowerCase() === round.toLocaleLowerCase() && [match.playerOneId, match.playerTwoId].sort().join('|') === pair)) errors.push(`Round ${round}: ${players.get(row.playerOneId)?.name} vs ${players.get(row.playerTwoId)?.name} already exists in this tournament.`);
    for (const playerId of [row.playerOneId, row.playerTwoId]) {
      const key = `${round.toLocaleLowerCase()}|${playerId}`;
      if (playedByRound.has(key)) errors.push(`Round ${round}: ${players.get(playerId)?.name} appears in more than one fixture.`);
      playedByRound.add(key);
    }
  }
  return [...new Set(errors)];
}

function downloadDrawTemplate(type: 'csv' | 'json') {
  const isCsv = type === 'csv';
  const body = isCsv ? 'player_one,player_two,round,table,start_time\n' : JSON.stringify({ schema_version: 1, matches: [{ player_one: '', player_two: '', round: 'Round 1', table: '', start_time: '' }] }, null, 2);
  const url = URL.createObjectURL(new Blob([body], { type: isCsv ? 'text/csv;charset=utf-8' : 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `rallydesk-draw-template.${type}`; link.click(); URL.revokeObjectURL(url);
}

function KnockoutPreview({ tournament, players }: { tournament: Tournament; players: Map<string, Player> }) {
  const entrants = tournament.entrantIds.map((id) => players.get(id)).filter((item): item is Player => Boolean(item));
  const stageCount = Math.max(1, Math.ceil(Math.log2(Math.max(entrants.length, 2))));
  const bracketSize = 2 ** stageCount;
  return <div className="bracket-preview">{Array.from({ length: stageCount }, (_, stage) => {
    const matchesInStage = bracketSize / (2 ** (stage + 1));
    const label = stage === 0 ? `ROUND OF ${bracketSize}` : stage === stageCount - 1 ? 'FINAL' : stage === stageCount - 2 ? 'SEMI-FINALS' : `ROUND ${stage + 1}`;
    return <div className={stage === 0 ? 'bracket-round' : `bracket-next${stage === stageCount - 1 ? ' bracket-next--final' : ''}`} key={label}><span className="bracket-round-label">{label}</span>{Array.from({ length: matchesInStage }, (_, index) => {
      const first = stage === 0 ? entrants[index * 2]?.name ?? 'BYE' : `Winner · Match ${String(index * 2 + 1).padStart(2, '0')}`;
      const second = stage === 0 ? entrants[index * 2 + 1]?.name ?? 'BYE' : `Winner · Match ${String(index * 2 + 2).padStart(2, '0')}`;
      return <div className={`bracket-match ${stage > 0 ? 'bracket-match--empty' : ''}`} key={index}><span>{first}</span><span>{second}</span></div>;
    })}{stage === stageCount - 1 && <span className="bracket-trophy"><Trophy size={19} /> Champion</span>}</div>;
  })}</div>;
}

function TournamentStandings({ tournament, players, matches }: { tournament: Tournament; players: Map<string, Player>; matches: Match[] }) {
  if (tournament.format === 'Knockout') return <section className="tournament-section standings-section"><div className="section-head"><div><p className="eyebrow">KNOCKOUT</p><h3>Progression</h3></div><span className="small-meta">Automatic round advancement</span></div><div className="progression-note"><ShieldCheck size={17} /><span>Winners advance after every match in a round is confirmed. The organiser can pause progression from the event overview.</span></div><div className="progression-entrants">{tournament.entrantIds.map((id, index) => { const firstRound = matches.find((match) => match.round === 'Round 1' && (match.playerOneId === id || match.playerTwoId === id)); const laterRound = matches.find((match) => Number(match.round?.match(/Round\s+(\d+)/i)?.[1] ?? 1) > 1 && (match.playerOneId === id || match.playerTwoId === id)); const state = tournament.byePlayerIds?.includes(id) ? 'Bye · advances' : laterRound ? laterRound.round : firstRound ? firstRound.status : 'Awaiting draw'; return <div className="progression-entrant" key={id}><span className="seed-number">{String(index + 1).padStart(2, '0')}</span><span className="avatar avatar--tiny">{players.get(id)?.initials}</span><b>{players.get(id)?.name ?? 'Unknown player'}</b><span className="entrant-rating">Seed {index + 1}</span><span className="progression-status">{state}</span></div>; })}</div></section>;
  const rows = [...tournament.standings].sort((a, b) => b.wins - a.wins || (b.gamesWon - b.gamesLost) - (a.gamesWon - a.gamesLost) || b.gamesWon - a.gamesWon);
  return <section className="tournament-section standings-section"><div className="section-head"><div><p className="eyebrow">ROUND ROBIN</p><h3>Current standings</h3><p className="section-caption">Ranked by {tournament.tieBreaks.join(', ').toLowerCase()}.</p></div><button className="button button-outline" onClick={() => downloadStandings(tournament, players)}><Download size={14} /> Export table</button></div><p className="table-scroll-hint"><ArrowRight size={13} /> Swipe or use arrow keys to view all columns</p><div className="standings-table-wrap" role="region" aria-label="Scrollable tournament standings" tabIndex={0}><table className="data-table standings-table"><thead><tr><th>POS</th><th>PLAYER</th><th>PLAYED</th><th>W</th><th>L</th><th>GAMES</th><th>DIFF</th><th>POINTS</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.playerId}><td><span className={`rank ${index === 0 ? 'rank--first' : ''}`}>{String(index + 1).padStart(2, '0')}</span></td><td><div className="standing-player"><span className="avatar avatar--tiny">{players.get(row.playerId)?.initials}</span><b>{players.get(row.playerId)?.name ?? 'Unknown player'}</b>{index === 0 && <span className="leader-mark">LEADER</span>}</div></td><td>{row.played}</td><td className="win-cell">{row.wins}</td><td>{row.losses}</td><td>{row.gamesWon}–{row.gamesLost}</td><td>{row.gamesWon - row.gamesLost > 0 ? '+' : ''}{row.gamesWon - row.gamesLost}</td><td>{row.pointsFor}–{row.pointsAgainst}</td></tr>)}</tbody></table></div><p className="table-footnote"><span /> Rankings reflect completed results only. Tie-break settings remain visible to organisers.</p></section>;
}

function TournamentAudit({ tournament }: { tournament: Tournament }) {
  return <section className="tournament-section audit-section"><div className="section-head"><div><p className="eyebrow">ORGANISER HISTORY</p><h3>Audit log</h3><p className="section-caption">Changes and the reason recorded with each one.</p></div><span className="audit-count">{tournament.audit.length} entries</span></div>{tournament.audit.length ? <div className="audit-list">{tournament.audit.map((entry) => <div className="audit-row" key={entry.id}><span className="audit-icon"><Activity size={15} /></span><div className="audit-copy"><b>{entry.action}</b><span>{entry.target}</span><small>Reason: {entry.reason}</small></div><time>{entry.at}</time></div>)}</div> : <div className="empty-draw"><span className="empty-mark"><ShieldCheck size={18} /></span><div><b>No organiser changes yet</b><span>Edits, corrections and progression decisions will be recorded here.</span></div></div>}</section>;
}

function TournamentMatchRow({ match, players, onClick, expanded = false }: { match: Match; players: Map<string, Player>; onClick: () => void; expanded?: boolean }) {
  const one = players.get(match.playerOneId); const two = players.get(match.playerTwoId);
  return <button className={`tournament-match-row ${expanded ? 'tournament-match-row--expanded' : ''}`} onClick={onClick}><div className="tournament-match-time"><b>{match.startsAt}</b><small>{match.table ?? 'No table'}</small></div><div className="tournament-match-pair"><span><b className={match.winnerId === one?.id ? 'winner-name' : ''}>{one?.name ?? 'Player one'}</b><span>{match.gamesWon[match.playerOneId] ?? 0}</span></span><span><b className={match.winnerId === two?.id ? 'winner-name' : ''}>{two?.name ?? 'Player two'}</b><span>{match.gamesWon[match.playerTwoId] ?? 0}</span></span></div><StatusPill status={match.status} /><ArrowRight className="match-row-arrow" size={15} /></button>;
}

function TournamentStatus({ status }: { status: Tournament['status'] }) {
  const className = status === 'Running' ? 'tournament-status tournament-status--running' : status === 'Completed' ? 'tournament-status tournament-status--complete' : status === 'Paused' ? 'tournament-status tournament-status--paused' : 'tournament-status tournament-status--upcoming';
  return <span className={className}><i />{status}</span>;
}

function ReasonDialog({ action, onClose, onConfirm }: { action: 'pause' | 'resume'; onClose: () => void; onConfirm: (reason: string) => void }) {
  const [reason, setReason] = useState(''); const isPause = action === 'pause';
  return <Dialog title={isPause ? 'Pause progression?' : 'Resume progression?'} eyebrow="ORGANISER DECISION" onClose={onClose}><form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (reason.trim()) onConfirm(reason.trim()); }}><p className="dialog-copy">{isPause ? 'Automatic advancement will stop. Matches and scores remain available for manual edits.' : 'Automatic progression will be available again after this decision is recorded.'}</p><label className="field"><span>Reason for this change</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder={isPause ? 'e.g. Review a disputed result' : 'e.g. Schedule confirmed'} required maxLength={160} /></label><div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={!reason.trim()}>{isPause ? <Pause size={15} /> : <Play size={15} />}{isPause ? 'Pause progression' : 'Resume progression'}</button></div></form></Dialog>;
}

function statusRank(status: Tournament['status']) { return status === 'Running' ? 0 : status === 'Paused' ? 1 : status === 'Upcoming' ? 2 : 3; }


function parseDrawCsv(source: string): Record<string, string>[] {
  const lines = source.replace(/^\uFEFF/, '').split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) return [];
  const parseLine = (line: string) => {
    const cells: string[] = []; let cell = ''; let quoted = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      if (char === '"' && quoted && line[index + 1] === '"') { cell += '"'; index += 1; }
      else if (char === '"') quoted = !quoted;
      else if (char === ',' && !quoted) { cells.push(cell.trim()); cell = ''; }
      else cell += char;
    }
    cells.push(cell.trim());
    return cells;
  };
  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => Object.fromEntries(parseLine(line).map((value, index) => [headers[index] ?? `column_${index}`, value])));
}


function downloadStandings(tournament: Tournament, players: Map<string, Player>) {
  const rows = [['position', 'player', 'played', 'wins', 'losses', 'games_won', 'games_lost', 'points_for', 'points_against'], ...tournament.standings.map((row, index) => [index + 1, players.get(row.playerId)?.name ?? '', row.played, row.wins, row.losses, row.gamesWon, row.gamesLost, row.pointsFor, row.pointsAgainst])];
  const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `${tournament.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-standings.csv`; link.click(); URL.revokeObjectURL(url);
}
