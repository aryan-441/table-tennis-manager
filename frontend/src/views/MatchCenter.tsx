import { useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, ChevronDown, CircleHelp, Clock3, Flag, Play, Timer, Undo2, X } from 'lucide-react';
import type { Match, Player, Workspace } from '../types';
import { Dialog } from '../components/Dialog';

type MatchCenterProps = { workspace: Workspace; players: Map<string, Player>; query: string; onQuery: (value: string) => void; onOpenMatch: (id: string) => void; onCreate: () => void };

export function MatchCenter({ workspace, players, query, onQuery, onOpenMatch, onCreate }: MatchCenterProps) {
  const [filter, setFilter] = useState<'All matches' | Match['status']>('All matches');
  const rows = useMemo(() => workspace.matches.filter((match) => {
    const term = query.toLowerCase();
    const names = `${players.get(match.playerOneId)?.name ?? ''} ${players.get(match.playerTwoId)?.name ?? ''} ${match.tournamentName ?? ''}`.toLowerCase();
    return (filter === 'All matches' || match.status === filter) && (!term || names.includes(term));
  }), [workspace.matches, players, query, filter]);
  const active = workspace.matches.filter((match) => match.status === 'In progress').length;
  const scheduled = workspace.matches.filter((match) => match.status === 'Scheduled').length;
  const complete = workspace.matches.filter((match) => match.status === 'Completed').length;
  return <div className="page-content">
    <div className="page-intro"><div><p className="eyebrow">COURT DESK</p><h2>Match schedule</h2><p>Track what’s on, start a scorecard, and pick up where a match left off.</p></div><div className="match-summary"><span><i className="summary-live-dot" />{active} live</span><span>{scheduled} scheduled</span><span>{complete} complete</span></div></div>
    <div className="toolbar-row"><div className="filter-tabs" role="tablist" aria-label="Filter matches">{(['All matches', 'In progress', 'Scheduled', 'Completed'] as const).map((item) => <button key={item} role="tab" aria-selected={filter === item} className={filter === item ? 'filter-tab filter-tab--active' : 'filter-tab'} onClick={() => setFilter(item)}>{item}{item === 'In progress' && active > 0 && <span className="filter-count">{active}</span>}</button>)}</div><label className="search-field"><span className="sr-only">Search matches</span><input type="search" placeholder="Find a player or event" value={query} onChange={(event) => onQuery(event.target.value)} /><CircleHelp size={15} /></label></div>
    <p className="table-scroll-hint"><ArrowRight size={13} /> Swipe or use arrow keys to view all columns</p>
    <div className="matches-table-wrap" role="region" aria-label="Scrollable match schedule" tabIndex={0}><table className="data-table matches-table"><thead><tr><th>Match</th><th>Event / round</th><th>Format</th><th>Table</th><th>Status</th><th>Score</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{rows.map((match) => <MatchRow key={match.id} match={match} players={players} onOpen={() => onOpenMatch(match.id)} />)}</tbody></table>
      {!rows.length && <div className="table-empty"><div className="empty-mark"><CircleHelp size={21} /></div><h3>{query ? 'No matches found' : 'Nothing on the schedule yet'}</h3><p>{query ? 'Try another player or event name.' : 'Set up a friendly or add a match to an event.'}</p>{!query && <button className="button button-primary" onClick={onCreate}>Create a match <ArrowRight size={15} /></button>}</div>}
    </div>
    <p className="table-footnote"><span /> Scores shown are from the current game. Match records are kept with their event history.</p>
  </div>;
}

function MatchRow({ match, players, onOpen }: { match: Match; players: Map<string, Player>; onOpen: () => void }) {
  const one = players.get(match.playerOneId); const two = players.get(match.playerTwoId);
  const scoreOne = match.status === 'Completed' ? match.gamesWon[match.playerOneId] ?? 0 : match.score[match.playerOneId] ?? 0;
  const scoreTwo = match.status === 'Completed' ? match.gamesWon[match.playerTwoId] ?? 0 : match.score[match.playerTwoId] ?? 0;
  return <tr className="match-row" onClick={onOpen} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') onOpen(); }}>
    <td><div className="match-cell-players"><span className="avatar avatar--tiny">{one?.initials ?? 'P1'}</span><div className="match-name-stack"><b className={match.winnerId === match.playerOneId ? 'winner-name' : ''}>{one?.name ?? 'Player one'}</b><b className={match.winnerId === match.playerTwoId ? 'winner-name' : ''}>{two?.name ?? 'Player two'}</b></div><span className="vs-mark">vs</span></div></td>
    <td><span className="event-name">{match.tournamentName ?? 'Club match'}</span><small className="event-round">{match.round ?? 'Unassigned'}</small></td>
    <td><span className="format-tag">{match.format}</span></td>
    <td><span className="table-label">{match.table ?? '—'}</span></td>
    <td><StatusPill status={match.status} /></td>
    <td><span className={`score-chip ${match.status === 'In progress' ? 'score-chip--live' : ''}`}>{scoreOne}<i>–</i>{scoreTwo}</span></td>
    <td><button className="row-open" aria-label={`Open ${one?.name} versus ${two?.name}`} onClick={(event) => { event.stopPropagation(); onOpen(); }}><ArrowRight size={16} /></button></td>
  </tr>;
}

export function StatusPill({ status }: { status: Match['status'] }) {
  const className = status === 'In progress' ? 'status-pill status-pill--live' : status === 'Completed' ? 'status-pill status-pill--complete' : status === 'Postponed' ? 'status-pill status-pill--paused' : 'status-pill status-pill--scheduled';
  return <span className={className}><i />{status}</span>;
}

type LiveProps = { match: Match; players: Map<string, Player>; onBack: () => void; onChange: (match: Match) => void; toast: (message: string) => void };

export function LiveScoring({ match, players, onBack, onChange, toast }: LiveProps) {
  const one = players.get(match.playerOneId)!; const two = players.get(match.playerTwoId)!;
  const [tossWinner, setTossWinner] = useState(match.tossWinnerId || match.playerOneId);
  const [serveChoice, setServeChoice] = useState<'serve' | 'receive'>('serve');
  const [undoOpen, setUndoOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [mobileActions, setMobileActions] = useState(false);
  const scoreOne = match.score[match.playerOneId] ?? 0; const scoreTwo = match.score[match.playerTwoId] ?? 0;
  const gameWinner = match.status === 'In progress' ? findGameWinner(match) : undefined;
  const matchWinner = match.winnerId ? players.get(match.winnerId) : undefined;
  const inProgress = match.status === 'In progress';
  const currentGameIndex = (match.gameResults?.length ?? 0) + 1;
  const servingPlayer = players.get(match.serverId) ?? one;
  const updateMatch = (next: Match) => onChange(next);

  const startMatch = () => {
    const firstServerId = serveChoice === 'serve' ? tossWinner : tossWinner === match.playerOneId ? match.playerTwoId : match.playerOneId;
    updateMatch({ ...match, status: 'In progress', tossWinnerId: tossWinner, serverId: firstServerId });
    toast('Match started');
  };

  const addPoint = (winnerId: string, kind: 'Point' | 'Fault' = 'Point') => {
    if (!inProgress || gameWinner) return;
    const before = { ...match.score };
    const nextScore = { ...before, [winnerId]: (before[winnerId] ?? 0) + 1 };
    const nextServer = serverForNextPoint(match, before, match.serverId);
    const event: Match['events'][number] = { id: crypto.randomUUID(), winnerId, score: `${nextScore[match.playerOneId]}–${nextScore[match.playerTwoId]}`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), kind };
    updateMatch({ ...match, score: nextScore, serverId: nextServer, events: [event, ...match.events] });
    if (kind === 'Fault') toast('Fault recorded · point awarded to receiver');
  };

  const addLet = () => {
    if (!inProgress || gameWinner) return;
    const event: Match['events'][number] = { id: crypto.randomUUID(), winnerId: match.serverId, score: `${scoreOne}–${scoreTwo}`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), kind: 'Let' };
    updateMatch({ ...match, events: [event, ...match.events] });
    toast('Let recorded · replay the point');
  };

  const undoPoint = (reason: string) => {
    const latestPoint = match.events.find((event) => event.kind === 'Point' || event.kind === 'Fault');
    if (!latestPoint) { toast('There is no point to undo'); setUndoOpen(false); return; }
    const [oneScore, twoScore] = latestPoint.score.split('–').map(Number);
    const beforeScore = latestPoint.winnerId === match.playerOneId ? { ...match.score, [match.playerOneId]: Math.max(0, oneScore - 1) } : { ...match.score, [match.playerTwoId]: Math.max(0, twoScore - 1) };
    const totalAfter = oneScore + twoScore;
    const oneBefore = beforeScore[match.playerOneId] ?? 0; const twoBefore = beforeScore[match.playerTwoId] ?? 0;
    const atDeuceBeforePoint = oneBefore >= match.pointsPerGame - 1 && twoBefore >= match.pointsPerGame - 1;
    const serviceInterval = atDeuceBeforePoint ? 1 : match.pointsPerGame === 11 ? 2 : 5;
    const serverChangedAfterPoint = totalAfter % serviceInterval === 0;
    const previousServerId = serverChangedAfterPoint ? match.serverId === match.playerOneId ? match.playerTwoId : match.playerOneId : match.serverId;
    const next = { ...match, score: beforeScore, serverId: previousServerId, events: [{ id: crypto.randomUUID(), winnerId: latestPoint.winnerId, score: latestPoint.score, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }), kind: 'Correction' as const }, ...match.events.filter((event) => event.id !== latestPoint.id)] };
    updateMatch(next); setUndoOpen(false); toast(`Last point removed · ${reason}`);
  };

  const acceptGame = () => {
    if (!gameWinner) return;
    const nextGames = { ...match.gamesWon, [gameWinner]: (match.gamesWon[gameWinner] ?? 0) + 1 };
    const matchWon = nextGames[gameWinner] >= match.gamesToWin;
    const completedGame = { one: scoreOne, two: scoreTwo, winnerId: gameWinner };
    const nextServer = match.serverId === match.playerOneId ? match.playerTwoId : match.playerOneId;
    updateMatch({ ...match, gamesWon: nextGames, gameResults: [...(match.gameResults ?? []), completedGame], score: matchWon ? match.score : { [match.playerOneId]: 0, [match.playerTwoId]: 0 }, status: matchWon ? 'Completed' : 'In progress', winnerId: matchWon ? gameWinner : undefined, serverId: nextServer, events: match.events });
    toast(matchWon ? 'Match result recorded' : 'Game confirmed · next game is ready');
  };

  return <div className="scoring-screen">
    <header className="scoring-topbar"><button className="scoring-back" onClick={onBack}><ArrowLeft size={17} /> <span>Match desk</span></button><span className="scoring-brand">rally<span>desk</span></span><div className="scoring-top-right"><StatusPill status={match.status} /><button className="icon-button scoring-help" onClick={() => setHelpOpen(true)} aria-label="Scoring help"><CircleHelp size={18} /></button></div></header>
    <main className="scoring-layout">
      <section className="scoring-main">
        <div className="scoring-match-meta"><div><p className="eyebrow">{match.tournamentName ?? 'CLUB MATCH'} <span className="eyebrow-rule" /> {match.round ?? 'FRIENDLY'}</p><h1>{one.name} <span>vs</span> {two.name}</h1><p className="scoring-meta-line"><span>{match.table ?? 'Table unassigned'}</span><i />{match.format}<i />First to {match.pointsPerGame}</p></div></div>
        {!inProgress && match.status !== 'Completed' && <section className="toss-panel"><div><p className="eyebrow">BEFORE THE FIRST SERVE</p><h2>Confirm the toss</h2><p>The toss winner chooses to serve or receive first.</p></div><div className="toss-controls"><div className="toss-player-choice"><span>Toss winner</span><div className="choice-pair"><button className={tossWinner === one.id ? 'choice-button choice-button--selected' : 'choice-button'} onClick={() => setTossWinner(one.id)}>{one.name}</button><button className={tossWinner === two.id ? 'choice-button choice-button--selected' : 'choice-button'} onClick={() => setTossWinner(two.id)}>{two.name}</button></div></div><div className="serve-choice"><span>Choice</span><div className="choice-pair choice-pair--short"><button className={serveChoice === 'serve' ? 'choice-button choice-button--selected' : 'choice-button'} onClick={() => setServeChoice('serve')}>Serve</button><button className={serveChoice === 'receive' ? 'choice-button choice-button--selected' : 'choice-button'} onClick={() => setServeChoice('receive')}>Receive</button></div></div><button className="button button-primary" onClick={startMatch}><Play size={15} fill="currentColor" /> Start match</button></div></section>}

        <div className={`scorecard ${match.status === 'Completed' ? 'scorecard--complete' : ''}`}>
          <div className="scorecard-top"><span><i className={inProgress ? 'score-live-dot' : 'score-done-dot'} />{match.status === 'Completed' ? 'FINAL SCORE' : inProgress ? `GAME ${currentGameIndex}` : 'MATCH RESULT'}</span><span>{match.status === 'Completed' ? 'Recorded' : `${match.pointsPerGame} POINT GAME`}</span></div>
          <div className="scorecard-players">
            <div className="scorecard-player"><div className="scorecard-person"><span className={`score-big-avatar ${matchWinner?.id === one.id ? 'score-big-avatar--winner' : ''}`}>{one.initials}</span><div><b>{one.name}</b><small>{one.style} <span>·</span> {one.hand.toLowerCase()} handed</small></div></div><span className="game-score">{match.gamesWon[one.id] ?? 0}</span><span className={`point-score ${!inProgress || match.serverId !== one.id ? 'point-score--muted' : ''}`}>{scoreOne}</span></div>
            <div className="scorecard-divider"><span /><span>SETS</span><span>POINTS</span></div>
            <div className="scorecard-player"><div className="scorecard-person"><span className={`score-big-avatar score-big-avatar--second ${matchWinner?.id === two.id ? 'score-big-avatar--winner' : ''}`}>{two.initials}</span><div><b>{two.name}</b><small>{two.style} <span>·</span> {two.hand.toLowerCase()} handed</small></div></div><span className="game-score">{match.gamesWon[two.id] ?? 0}</span><span className={`point-score point-score--second ${!inProgress || match.serverId !== two.id ? 'point-score--muted' : ''}`}>{scoreTwo}</span></div>
          </div>
          {match.status === 'Completed' && <div className="match-final-strip"><Check size={16} /><span><b>{matchWinner?.name}</b> won the match</span><span>{match.format} · {match.gamesWon[one.id]}–{match.gamesWon[two.id]}</span></div>}
          {inProgress && <div className="serve-bar"><span className="serve-ball">●</span><span><b>{servingPlayer.name}</b> to serve next</span><span className="serve-bar-note">Serve changes automatically</span></div>}
        </div>

        {inProgress && <>
          {gameWinner ? <div className="game-won-banner"><div><span className="eyebrow">GAME POINT</span><b>{players.get(gameWinner)?.name} takes the game</b></div><button className="button button-primary" onClick={acceptGame}><Check size={16} /> Confirm game result</button><button className="undo-game" onClick={() => setUndoOpen(true)}><Undo2 size={15} /> Undo last point</button></div> : <div className="score-controls"><div className="score-control-heading"><span>POINT WON BY</span><span>Tap a player to add a point</span></div><div className="point-buttons"><button className="point-button" onClick={() => addPoint(one.id)}><span className="point-plus">+</span><span><small>POINT FOR</small><b>{one.name}</b></span><span className="point-shortcut">A</span></button><span className="point-separator">OR</span><button className="point-button point-button--orange" onClick={() => addPoint(two.id)}><span className="point-plus">+</span><span><small>POINT FOR</small><b>{two.name}</b></span><span className="point-shortcut">L</span></button></div><div className="score-secondary-actions"><button onClick={addLet}><span className="let-icon">↻</span> Let · replay point</button><button onClick={() => addPoint(match.serverId === one.id ? two.id : one.id, 'Fault')}><Flag size={14} /> Fault · point to receiver</button><button onClick={() => setUndoOpen(true)} disabled={!match.events.some((event) => event.kind === 'Point' || event.kind === 'Fault')}><Undo2 size={14} /> Undo last point</button></div></div>}
        </>}
        <div className="game-history"><div className="section-head"><div><p className="eyebrow">MATCH RECORD</p><h3>Games so far</h3></div><span className="small-meta">Best of {match.gamesToWin * 2 - 1}</span></div><div className="game-history-list">{match.gameResults?.length ? match.gameResults.map((game, index) => <div className="game-history-row" key={`${index}-${game.winnerId}`}><span className="game-number">GAME {String(index + 1).padStart(2, '0')}</span><span className={game.winnerId === one.id ? 'game-result game-result--winner' : 'game-result'}>{game.one}</span><i>–</i><span className={game.winnerId === two.id ? 'game-result game-result--winner' : 'game-result'}>{game.two}</span><span className="game-winner-name">{players.get(game.winnerId)?.name} won</span><Check size={15} /></div>) : <div className="history-placeholder"><span>GAMES WILL APPEAR HERE</span><span>Each accepted result is kept in the match record.</span></div>}</div></div>
      </section>

      <aside className={`scoring-aside ${mobileActions ? 'scoring-aside--open' : ''}`}>
        <div className="aside-head"><div><p className="eyebrow">POINT BY POINT</p><h3>Match timeline</h3></div><span className="timeline-count">{match.events.length}</span><button className="timeline-mobile-close icon-button" onClick={() => setMobileActions(false)} aria-label="Close timeline"><X size={17} /></button></div>
        <div className="timeline-info"><span><Timer size={14} /> {match.events[0]?.time ?? 'Awaiting first point'}</span>{match.events.length > 12 && <button onClick={() => setShowAllEvents((shown) => !shown)}><ChevronDown size={14} /> {showAllEvents ? 'Show recent' : `All ${match.events.length} events`}</button>}</div>
        <div className="timeline-list">{match.events.length ? (showAllEvents ? match.events : match.events.slice(0, 12)).map((event, index) => <div className={`timeline-event ${event.kind === 'Correction' ? 'timeline-event--correction' : ''}`} key={event.id}><div className="timeline-rail"><span className={`timeline-node timeline-node--${event.kind.toLowerCase()}`}>{event.kind === 'Let' ? '↻' : event.kind === 'Fault' ? '!' : event.kind === 'Correction' ? '↶' : index + 1}</span>{index < (showAllEvents ? match.events.length : Math.min(match.events.length, 12)) - 1 && <i />}</div><div className="timeline-copy"><b>{event.kind === 'Point' ? `${players.get(event.winnerId)?.name} won point` : event.kind === 'Fault' ? `Fault · point to ${players.get(event.winnerId)?.name}` : event.kind === 'Let' ? 'Let · replay point' : 'Point corrected'}</b><span>{event.score} <i>·</i> {event.time}</span></div></div>) : <div className="timeline-empty"><div className="timeline-empty-mark">○</div><b>No points recorded yet</b><span>The timeline will build as the match is scored.</span></div>}</div>
        <div className="timeline-footer"><span><Clock3 size={14} /> Started {inProgress ? 'today' : 'not started'}</span><span>{match.events.length} recorded events</span></div>
      </aside>
      <button className="mobile-timeline-fab" onClick={() => setMobileActions(true)}><Timer size={16} /> Match timeline <span>{match.events.length}</span></button>
    </main>
    <footer className="app-footer scoring-footer"><span>Rallydesk</span><a href="mailto:rallydesksupport@gmail.com">Support · rallydesksupport@gmail.com</a><span>© Aryan Arora 2026</span></footer>
    {undoOpen && <UndoDialog onClose={() => setUndoOpen(false)} onConfirm={undoPoint} />}
    {helpOpen && <ScoringHelpDialog onClose={() => setHelpOpen(false)} />}
  </div>;
}

function UndoDialog({ onClose, onConfirm }: { onClose: () => void; onConfirm: (reason: string) => void }) {
  const [reason, setReason] = useState('');
  return <Dialog title="Undo the last point?" eyebrow="CORRECTION" onClose={onClose}><form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (reason.trim()) onConfirm(reason.trim()); }}><p className="dialog-copy">This adds a correction to the match timeline and removes the most recent point from the score.</p><label className="field"><span>Reason for correction</span><input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="e.g. Point was awarded to the wrong player" required maxLength={160} /></label><div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Keep point</button><button className="button button-danger" type="submit" disabled={!reason.trim()}><Undo2 size={15} /> Undo point</button></div></form></Dialog>;
}

function serverForNextPoint(match: Match, scoreBefore: Record<string, number>, currentServer: string) {
  const totalAfter = (scoreBefore[match.playerOneId] ?? 0) + (scoreBefore[match.playerTwoId] ?? 0) + 1;
  const atDeuce = (scoreBefore[match.playerOneId] ?? 0) >= match.pointsPerGame - 1 && (scoreBefore[match.playerTwoId] ?? 0) >= match.pointsPerGame - 1;
  const interval = atDeuce ? 1 : match.pointsPerGame === 11 ? 2 : 5;
  return totalAfter % interval === 0 ? currentServer === match.playerOneId ? match.playerTwoId : match.playerOneId : currentServer;
}

function findGameWinner(match: Match): string | undefined {
  const one = match.score[match.playerOneId] ?? 0; const two = match.score[match.playerTwoId] ?? 0;
  const target = match.pointsPerGame;
  if (one >= target && one - two >= 2) return match.playerOneId;
  if (two >= target && two - one >= 2) return match.playerTwoId;
  return undefined;
}

function ScoringHelpDialog({ onClose }: { onClose: () => void }) {
  return <Dialog title="Using the scorecard" eyebrow="SCORING GUIDE" onClose={onClose}>
    <div className="scoring-help-copy"><p>Confirm who won the toss and whether they chose to serve or receive, then start the match.</p><p>Tap the player who won each point. Rallydesk rotates service, applies win-by-two at deuce, and records lets, faults and corrections in the timeline.</p><p>When a game reaches its winning score, confirm the game result to continue. The match is recorded when a player reaches the configured games-to-win total.</p></div>
    <div className="dialog-actions"><button className="button button-primary" onClick={onClose}>Got it</button></div>
  </Dialog>;
}
