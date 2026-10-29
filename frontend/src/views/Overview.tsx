import { ArrowRight, Clock3, Radio, Trophy, Users } from 'lucide-react';
import type { Match, Player, PageId, Workspace } from '../types';

type OverviewProps = { workspace: Workspace; players: Map<string, Player>; onOpenMatch: (id: string) => void; onPage: (page: PageId) => void; onNewMatch: () => void; onNewTournament: () => void; onNewPlayer: () => void };

export function Overview({ workspace, players, onOpenMatch, onPage, onNewMatch, onNewTournament, onNewPlayer }: OverviewProps) {
  const live = workspace.matches.find((match) => match.status === 'In progress');
  const upcoming = workspace.matches.filter((match) => match.status === 'Scheduled').slice(0, 4);
  const activeTournament = workspace.tournaments.find((item) => item.status === 'Running');
  const completeMatches = workspace.matches.filter((match) => match.status === 'Completed').length;
  const topRows = activeTournament?.standings.slice(0, 4) ?? [];
  const today = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' }).format(new Date()).toUpperCase();
  const tablesInUse = new Set(workspace.matches.map((match) => match.table).filter(Boolean)).size;

  return <div className="page-content overview-page">
    <div className="welcome-line"><div><p className="eyebrow">{today} <span className="eyebrow-rule" /> {workspace.clubName || 'YOUR CLUB'}</p><h2>Your club desk<span className="greeting-period">.</span></h2><p className="welcome-sub">Add players, schedule a match, or build your next tournament.</p></div><div className="overview-quick">{workspace.players.length < 2 ? <button className="text-action" onClick={onNewPlayer}><Users size={15} /> Add your first player</button> : <><button className="text-action" onClick={onNewTournament}><Trophy size={15} /> Plan a tournament</button><button className="text-action" onClick={onPage.bind(null, 'players')}><Users size={15} /> View players</button></>}</div></div>

    <section className="today-board" aria-label="Today's match">
      <div className="today-board-main">
        <div className="board-heading"><span className="live-label"><i /> {live ? 'LIVE MATCH' : 'CLUB SNAPSHOT'}</span><span className="board-context">{live ? `${live.table ?? 'Table not assigned'} · ${live.tournamentName ?? 'Friendly match'}` : workspace.clubName || 'Your workspace'}</span></div>
        {live ? <>
          <div className="scoreboard">
            <div className="score-player"><span className="score-avatar">{players.get(live.playerOneId)?.initials ?? 'P1'}</span><span className="score-player-name">{players.get(live.playerOneId)?.name ?? 'Player one'}</span><small>{live.playerOneId === live.serverId ? 'SERVING' : 'RECEIVING'}</small></div>
            <div className="score-numbers"><span>{live.gamesWon[live.playerOneId] ?? 0}</span><b>—</b><span>{live.gamesWon[live.playerTwoId] ?? 0}</span><small>GAMES</small></div>
            <div className="score-player score-player--right"><span className="score-player-name">{players.get(live.playerTwoId)?.name ?? 'Player two'}</span><span className="score-avatar score-avatar--orange">{players.get(live.playerTwoId)?.initials ?? 'P2'}</span><small>{live.playerTwoId === live.serverId ? 'SERVING' : 'RECEIVING'}</small></div>
          </div>
          <div className="board-footer"><span className="current-points"><b>{live.score[live.playerOneId] ?? 0}</b><i>:</i><b>{live.score[live.playerTwoId] ?? 0}</b><small>CURRENT GAME</small></span><span className="board-format">{live.format} <span>·</span> first to {live.pointsPerGame}</span><button className="button button-board" onClick={() => onOpenMatch(live.id)}>Open scoring <ArrowRight size={15} /></button></div>
        </> : <div className="board-empty"><div className="empty-ball">●</div><div><h3>{workspace.players.length < 2 ? 'Add players to get started' : 'No match is in progress'}</h3><p>{workspace.players.length < 2 ? 'Create player profiles first, then set up a singles match or tournament.' : 'Start a match when players are ready at the table.'}</p></div><button className="button button-board" onClick={workspace.players.length < 2 ? onNewPlayer : onNewMatch}>{workspace.players.length < 2 ? 'Add a player' : 'Set up a match'} <ArrowRight size={15} /></button></div>}
      </div>
      <div className="today-board-side"><div className="board-side-kicker">TODAY SO FAR</div><div className="metric-row"><span>Matches played</span><b>{completeMatches}<small> / {workspace.matches.length}</small></b></div><div className="metric-row"><span>Players on roster</span><b>{workspace.players.length}</b></div><div className="metric-row"><span>Tables in use</span><b>{tablesInUse}</b></div><div className="side-rule" /><button className="side-link" onClick={() => onPage('matches')}>View match schedule <ArrowRight size={14} /></button></div>
    </section>

    <div className="overview-columns">
      <section className="section-block schedule-block">
        <div className="section-head"><div><p className="eyebrow">THE NEXT ROTATION</p><h3>Up next</h3></div><button className="quiet-link" onClick={() => onPage('matches')}>Full schedule <ArrowRight size={14} /></button></div>
        {upcoming.length ? <div className="schedule-list">{upcoming.map((match, index) => <ScheduleRow key={match.id} match={match} players={players} index={index} onOpen={() => onOpenMatch(match.id)} />)}</div> : <div className="inline-empty"><Clock3 size={18} /><span>No matches are waiting. Add one to the schedule.</span><button onClick={onNewMatch}>Create match</button></div>}
      </section>
      <section className="section-block standings-block">
        <div className="section-head"><div><p className="eyebrow">{activeTournament?.name ?? 'TOURNAMENT DESK'}</p><h3>Current standings</h3></div><button className="icon-button section-more" aria-label="Open tournament" onClick={() => onPage('tournaments')}><ArrowRight size={15} /></button></div>
        {topRows.length ? <>
          <div className="standings-header"><span>PLAYER</span><span>W–L</span><span>GAMES</span></div>
          <div className="standings-list">{topRows.map((row, index) => { const player = players.get(row.playerId); return <div className="standing-row" key={row.playerId}><span className={`rank ${index === 0 ? 'rank--first' : ''}`}>{String(index + 1).padStart(2, '0')}</span><span className="standing-player"><span className="avatar avatar--tiny">{player?.initials}</span><b>{player?.name ?? 'Unknown player'}</b></span><span className="standing-record">{row.wins}–{row.losses}</span><span className="standing-games">{row.gamesWon}–{row.gamesLost}</span></div>; })}</div>
          <button className="standings-footer" onClick={() => onPage('tournaments')}>Full table <ArrowRight size={14} /></button>
        </> : <div className="empty-standings"><Trophy size={20} /><p>Standings appear when a tournament has results.</p><button className="quiet-link" onClick={onNewTournament}>Create a tournament <ArrowRight size={14} /></button></div>}
      </section>
    </div>

    <section className="bottom-strip"><div className="bottom-strip-icon"><Radio size={18} /></div><div className="bottom-strip-copy"><b>{activeTournament ? activeTournament.name : 'Your tournament desk'}</b><span>{activeTournament ? `${activeTournament.completed} of ${activeTournament.matchIds.length || activeTournament.rounds} matches completed · ${activeTournament.entrantIds.length} entrants` : 'Create an event, manage the draw and keep every result in one place.'}</span></div><div className="bottom-strip-status"><span className={`status-dot ${activeTournament?.progressPaused ? 'status-dot--paused' : ''}`} />{activeTournament?.progressPaused ? 'Progression paused' : activeTournament ? 'In progress' : 'Ready when you are'}</div><button className="bottom-strip-action" onClick={activeTournament ? () => onPage('tournaments') : onNewTournament}>{activeTournament ? 'Open tournament' : 'Set up tournament'} <ArrowRight size={14} /></button></section>
  </div>;
}

function ScheduleRow({ match, players, index, onOpen }: { match: Match; players: Map<string, Player>; index: number; onOpen: () => void }) {
  const one = players.get(match.playerOneId); const two = players.get(match.playerTwoId);
  return <button className="schedule-row" onClick={onOpen}><span className="schedule-time"><b>{match.startsAt}</b><small>{index === 0 ? 'NEXT' : match.table}</small></span><span className="schedule-match"><span><b>{one?.name ?? 'Player one'}</b><i>vs</i><b>{two?.name ?? 'Player two'}</b></span><small>{match.tournamentName ?? 'Friendly match'} <span>·</span> {match.format}</small></span><span className="schedule-table">{match.table ?? 'Unassigned'}</span><span className="schedule-arrow"><ArrowRight size={15} /></span></button>;
}
