import { useEffect, useMemo, useRef, useState } from 'react';
import { Activity, ArrowRight, Bell, ChartNoAxesCombined, CircleDot, ClipboardList, Download, Info, Menu, Plus, Settings2, Table2, Trophy, Users, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { createMatch, createPlayer, createTournament, generateKnockoutRoundFixtures, generateTournamentFixtures, loadWorkspace, resetWorkspace, saveWorkspace } from './services/store';
import type { Match, PageId, Player, Tournament, Workspace } from './types';
import { Overview } from './views/Overview';
import { MatchCenter, LiveScoring } from './views/MatchCenter';
import { PlayersView } from './views/PlayersView';
import { TournamentsView } from './views/TournamentsView';
import { StatisticsView } from './views/StatisticsView';
import { AboutView, ExportsView, SettingsView } from './views/UtilityViews';
import { Dialog } from './components/Dialog';

type NavItem = { id: PageId; label: string; icon: LucideIcon };
const mainNav: NavItem[] = [
  { id: 'overview', label: 'Overview', icon: Table2 },
  { id: 'matches', label: 'Matches', icon: CircleDot },
  { id: 'tournaments', label: 'Tournaments', icon: Trophy },
  { id: 'players', label: 'Players', icon: Users },
  { id: 'statistics', label: 'Statistics', icon: ChartNoAxesCombined },
];
const workspaceNav: NavItem[] = [
  { id: 'exports', label: 'Exports & recovery', icon: Download },
  { id: 'settings', label: 'Settings', icon: Settings2 },
  { id: 'about', label: 'About Rallydesk', icon: Info },
];
const pageTitles: Record<PageId, string> = {
  overview: 'Rallydesk', matches: 'Matches', tournaments: 'Tournaments', players: 'Players', statistics: 'Statistics', exports: 'Exports & recovery', settings: 'Workspace settings', about: 'About Rallydesk',
};

type CreateDialog = 'player' | 'match' | 'tournament' | null;

export default function App() {
  const [workspace, setWorkspace] = useState<Workspace>(loadWorkspace);
  const [page, setPage] = useState<PageId>('overview');
  const [createDialog, setCreateDialog] = useState<CreateDialog>(null);
  const [activeMatchId, setActiveMatchId] = useState<string | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null);
  const [selectedTournamentId, setSelectedTournamentId] = useState<string | null>(null);
  const [toast, setToast] = useState('');
  const [mobileNav, setMobileNav] = useState(false);
  const mobileMenuRef = useRef<HTMLButtonElement>(null);
  const mobileCloseRef = useRef<HTMLButtonElement>(null);
  const sidebarRef = useRef<HTMLElement>(null);
  const previousMobileNav = useRef(false);
  const [query, setQuery] = useState('');
  const [showQuickActions, setShowQuickActions] = useState(false);

  useEffect(() => { if (!saveWorkspace(workspace)) setToast('This browser blocked workspace storage. Changes may not persist after reload.'); }, [workspace]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(''), 3200);
    return () => window.clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (previousMobileNav.current === mobileNav) return;
    previousMobileNav.current = mobileNav;
    if (mobileNav) mobileCloseRef.current?.focus();
    else mobileMenuRef.current?.focus();
  }, [mobileNav]);
  useEffect(() => {
    if (!mobileNav) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setMobileNav(false); return; }
      if (event.key !== 'Tab') return;
      const focusable = sidebarRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled])');
      if (!focusable?.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1]; const active = document.activeElement;
      if (event.shiftKey && (active === first || !sidebarRef.current?.contains(active))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (active === last || !sidebarRef.current?.contains(active))) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mobileNav]);

  const playerById = useMemo(() => new Map(workspace.players.map((player) => [player.id, player])), [workspace.players]);
  const activeMatch = workspace.matches.find((match) => match.id === activeMatchId) ?? null;

  useEffect(() => {
    document.title = activeMatch ? 'Live scoring — Rallydesk' : page === 'overview' ? 'Rallydesk — Table Tennis Manager' : `${pageTitles[page]} — Rallydesk`;
  }, [activeMatch?.id, page]);

  const update = (mutator: (current: Workspace) => Workspace) => setWorkspace((current) => mutator(structuredClone(current)));
  const saveScoredMatch = (next: Match) => update((current) => {
    let matches = current.matches.map((match) => match.id === next.id ? next : match);
    const finished = matches.filter((match) => match.status === 'Completed' && match.winnerId);
    const players = current.players.map((player) => {
      const played = finished.filter((match) => match.playerOneId === player.id || match.playerTwoId === player.id);
      return {
        ...player,
        wins: played.filter((match) => match.winnerId === player.id).length,
        losses: played.filter((match) => match.winnerId !== player.id).length,
        pointsWon: matches.flatMap((match) => match.events).filter((event) => event.winnerId === player.id && (event.kind === 'Point' || event.kind === 'Fault')).length,
        recent: played.slice(0, 5).map((match) => match.winnerId === player.id ? 'W' as const : 'L' as const),
      };
    });
    const tournaments = current.tournaments.map((tournament) => {
      let eventMatches = matches.filter((match) => match.tournamentId === tournament.id || tournament.matchIds.includes(match.id));
      let completed = eventMatches.filter((match) => match.status === 'Completed' && match.winnerId);
      let currentRound = Math.max(0, ...eventMatches.map((match) => Number(match.round?.match(/Round\s+(\d+)/i)?.[1] ?? 0)));
      let updatedTournament = tournament;
      if (tournament.format === 'Knockout' && !tournament.progressPaused && currentRound > 0 && currentRound < tournament.rounds) {
        const roundMatches = eventMatches.filter((match) => match.round === `Round ${currentRound}`);
        const hasNextRound = eventMatches.some((match) => match.round === `Round ${currentRound + 1}`);
        if (roundMatches.length && roundMatches.every((match) => match.status === 'Completed' && match.winnerId) && !hasNextRound) {
          const qualifiers = [ ...(currentRound === 1 ? tournament.byePlayerIds ?? [] : []), ...roundMatches.map((match) => match.winnerId!) ]
            .sort((one, two) => tournament.entrantIds.indexOf(one) - tournament.entrantIds.indexOf(two));
          const fixtures = generateKnockoutRoundFixtures(tournament, qualifiers, currentRound + 1);
          matches = [...fixtures, ...matches];
          updatedTournament = { ...tournament, matchIds: [...tournament.matchIds, ...fixtures.map((match) => match.id)] };
          eventMatches = [...fixtures, ...eventMatches];
          completed = eventMatches.filter((match) => match.status === 'Completed' && match.winnerId);
          currentRound += 1;
        }
      }
      const rows = new Map(tournament.entrantIds.map((playerId) => [playerId, { playerId, played: 0, wins: 0, losses: 0, gamesWon: 0, gamesLost: 0, pointsFor: 0, pointsAgainst: 0 }]));
      for (const match of completed) {
        const one = rows.get(match.playerOneId); const two = rows.get(match.playerTwoId);
        if (!one || !two) continue;
        one.played += 1; two.played += 1;
        if (match.winnerId === one.playerId) { one.wins += 1; two.losses += 1; } else { two.wins += 1; one.losses += 1; }
        one.gamesWon += match.gamesWon[match.playerOneId] ?? 0; one.gamesLost += match.gamesWon[match.playerTwoId] ?? 0;
        two.gamesWon += match.gamesWon[match.playerTwoId] ?? 0; two.gamesLost += match.gamesWon[match.playerOneId] ?? 0;
        for (const game of match.gameResults ?? []) { one.pointsFor += game.one; one.pointsAgainst += game.two; two.pointsFor += game.two; two.pointsAgainst += game.one; }
      }
      const complete = eventMatches.length > 0 && completed.length === eventMatches.length && (tournament.format !== 'Knockout' || currentRound >= tournament.rounds);
      return { ...updatedTournament, standings: [...rows.values()], completed: completed.length, status: tournament.progressPaused ? 'Paused' as const : complete ? 'Completed' as const : completed.length ? 'Running' as const : tournament.status };
    });
    return { ...current, matches, players, tournaments };
  });
  const openMatchSetup = () => {
    if (workspace.players.length < 2) { setPage('players'); setToast('Add at least two players before setting up a match'); return; }
    setCreateDialog('match');
  };
  const openTournamentSetup = () => {
    if (workspace.players.length < 2) { setPage('players'); setToast('Add at least two players before creating a tournament'); return; }
    setCreateDialog('tournament');
  };
  const createNewPlayer = (name: string, hand: Player['hand'], grip: Player['grip'], style: string) => {
    const player = createPlayer(name, hand, grip, style);
    update((current) => ({ ...current, players: [player, ...current.players] }));
    setCreateDialog(null);
    setSelectedPlayerId(player.id);
    setPage('players');
    setToast(`${player.name} added to the player list`);
  };
  const createNewMatch = (input: Pick<Match, 'playerOneId' | 'playerTwoId' | 'format' | 'pointsPerGame' | 'gamesToWin' | 'tournamentId' | 'table'>) => {
    if (input.playerOneId === input.playerTwoId) { setToast('Choose two different players'); return; }
    const match = createMatch(input, workspace.players);
    const tournament = workspace.tournaments.find((item) => item.id === input.tournamentId);
    if (tournament) match.tournamentName = tournament.name;
    update((current) => ({ ...current, matches: [match, ...current.matches], tournaments: current.tournaments.map((item) => item.id === input.tournamentId ? { ...item, matchIds: [match.id, ...item.matchIds] } : item) }));
    setCreateDialog(null);
    setActiveMatchId(match.id);
    setToast('Match created. Confirm the toss and first server to begin.');
  };
  const createNewTournament = (input: Pick<Tournament, 'name' | 'format' | 'date' | 'venue' | 'entrantIds'>) => {
    const tournament = createTournament(input);
    const fixtures = generateTournamentFixtures(tournament, workspace.players);
    tournament.matchIds = fixtures.map((match) => match.id);
    update((current) => ({ ...current, matches: [...fixtures, ...current.matches], tournaments: [tournament, ...current.tournaments] }));
    setCreateDialog(null);
    setSelectedTournamentId(tournament.id);
    setPage('tournaments');
    setToast(`${tournament.name} created · ${fixtures.length} opening fixtures generated`);
  };
  const replaceWorkspace = (next: Workspace) => { setWorkspace(next); setToast('Workspace updated'); };
  const reset = () => { setWorkspace(resetWorkspace()); setPage('overview'); setSelectedPlayerId(null); setSelectedTournamentId(null); setToast('Workspace cleared'); };

  if (activeMatch) {
    return <LiveScoring match={activeMatch} players={playerById} onBack={() => setActiveMatchId(null)} onChange={saveScoredMatch} toast={setToast} />;
  }

  return (
    <div className="app-frame">
      {mobileNav && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
      <aside ref={sidebarRef} id="rallydesk-sidebar" aria-label="Primary navigation" className={`sidebar ${mobileNav ? 'sidebar--open' : ''}`}>
        <div className="brand-lockup"><span className="brand-mark"><i /><i /><i /></span><span>rally<span className="brand-light">desk</span><small>CLUB OPERATIONS</small></span><button ref={mobileCloseRef} className="mobile-close icon-button" onClick={() => setMobileNav(false)} aria-label="Close navigation"><X size={18} /></button></div>
        <button className="club-switcher" onClick={() => setPage('settings')}><span className="club-monogram">{workspace.clubName?.trim().charAt(0).toUpperCase() || '＋'}</span><span><b>{workspace.clubName || 'Add your club name'}</b><small>Workspace settings</small></span><span className="switch-caret">⌄</span></button>
        <nav aria-label="Main navigation">
          <p className="nav-label">CLUB</p>
          {mainNav.map((item) => <NavButton key={item.id} item={item} active={page === item.id} count={item.id === 'matches' ? workspace.matches.filter((match) => match.status === 'In progress').length : undefined} onClick={() => { setPage(item.id); setSelectedPlayerId(null); setSelectedTournamentId(null); setMobileNav(false); }} />)}
          <p className="nav-label nav-label--spaced">MANAGE</p>
          {workspaceNav.map((item) => <NavButton key={item.id} item={item} active={page === item.id} onClick={() => { setPage(item.id); setMobileNav(false); }} />)}
        </nav>
        <div className="sidebar-bottom">
          <div className="storage-note"><span className="storage-dot" /><span><b>Local preview</b><small>Saved in this browser</small></span></div>
          
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <button ref={mobileMenuRef} className="mobile-menu icon-button" onClick={() => setMobileNav(true)} aria-label="Open navigation" aria-expanded={mobileNav} aria-controls="rallydesk-sidebar"><Menu size={20} /></button>
          <div className="breadcrumb"><span>{workspace.clubName || 'Rallydesk'}</span><span className="breadcrumb-slash">/</span><b>{pageTitles[page]}</b></div>
          <div className="topbar-right">
            <span className="preview-pill"><span /> Local preview</span>
            <button className="topbar-icon icon-button" aria-label="Notifications" onClick={() => setToast('You’re all caught up')}><Bell size={18} /><i /></button>
          </div>
        </header>

        <main className="page-wrap">
          <div className="page-toolbar">
            <div className="mobile-page-title"><span className="eyebrow">{workspace.clubName || 'YOUR CLUB'} · {new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date()).toUpperCase()}</span><h1>{pageTitles[page]}</h1></div>
            <div className="quick-actions-wrap">
              <button className="button button-primary" onClick={openMatchSetup}><Plus size={17} strokeWidth={2.5} /> New match</button>
              <button className="button button-icon" onClick={() => setShowQuickActions((value) => !value)} aria-label="More create actions"><span>···</span></button>
              {showQuickActions && <div className="quick-actions-menu"><button onClick={() => { openTournamentSetup(); setShowQuickActions(false); }}><Trophy size={16} /> New tournament</button><button onClick={() => { setCreateDialog('player'); setShowQuickActions(false); }}><Users size={16} /> Add player</button></div>}
            </div>
          </div>

          {page === 'overview' && <Overview workspace={workspace} players={playerById} onOpenMatch={setActiveMatchId} onPage={setPage} onNewMatch={openMatchSetup} onNewTournament={openTournamentSetup} onNewPlayer={() => setCreateDialog('player')} />}
          {page === 'matches' && <MatchCenter workspace={workspace} players={playerById} query={query} onQuery={setQuery} onOpenMatch={setActiveMatchId} onCreate={openMatchSetup} />}
          {page === 'players' && <PlayersView workspace={workspace} query={query} onQuery={setQuery} selectedId={selectedPlayerId} onSelect={setSelectedPlayerId} onAdd={() => setCreateDialog('player')} onMatch={(id) => { setSelectedPlayerId(null); setCreateDialog('match'); if (id) setToast('Choose this player in the match setup.'); }} />}
          {page === 'tournaments' && <TournamentsView workspace={workspace} players={playerById} selectedId={selectedTournamentId} onSelect={setSelectedTournamentId} onCreate={openTournamentSetup} onOpenMatch={setActiveMatchId} onChange={(next) => replaceWorkspace(next)} toast={setToast} />}
          {page === 'statistics' && <StatisticsView workspace={workspace} />}
          {page === 'exports' && <ExportsView workspace={workspace} onToast={setToast} />}
          {page === 'settings' && <SettingsView workspace={workspace} clubName={workspace.clubName ?? ''} onSaveClubName={(name) => { update((current) => ({ ...current, clubName: name })); setToast(name ? `${name} saved` : 'Club name cleared'); }} onImportWorkspace={replaceWorkspace} onReset={reset} />}
          {page === 'about' && <AboutView />}
        </main>
        <footer className="app-footer"><span>Rallydesk</span><a href="mailto:rallydesksupport@gmail.com">Support · rallydesksupport@gmail.com</a><span>© Aryan Arora 2026</span></footer>
      </div>

      {createDialog === 'player' && <PlayerDialog onClose={() => setCreateDialog(null)} onCreate={createNewPlayer} />}
      {createDialog === 'match' && <MatchDialog players={workspace.players} tournaments={workspace.tournaments} onClose={() => setCreateDialog(null)} onCreate={createNewMatch} />}
      {createDialog === 'tournament' && <TournamentDialog players={workspace.players} onClose={() => setCreateDialog(null)} onCreate={createNewTournament} />}
      {toast && <div className="toast" role="status"><span className="toast-dot" />{toast}</div>}
    </div>
  );
}

function NavButton({ item, active, count, onClick }: { item: NavItem; active: boolean; count?: number; onClick: () => void }) {
  const Icon = item.icon;
  return <button className={`nav-item ${active ? 'nav-item--active' : ''}`} onClick={onClick} aria-current={active ? 'page' : undefined}><Icon size={17} strokeWidth={active ? 2.25 : 1.8} /><span>{item.label}</span>{Boolean(count) && <span className="nav-count">{count}</span>}</button>;
}

function PlayerDialog({ onClose, onCreate }: { onClose: () => void; onCreate: (name: string, hand: Player['hand'], grip: Player['grip'], style: string) => void }) {
  const [name, setName] = useState('');
  const [hand, setHand] = useState<Player['hand']>('Right');
  const [grip, setGrip] = useState<Player['grip']>('Shakehand');
  const [style, setStyle] = useState('Attacker');
  return <Dialog title="Add a player" eyebrow="PLAYER PROFILE" onClose={onClose}><form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (name.trim()) onCreate(name, hand, grip, style); }}>
    <label className="field"><span>Player name</span><input autoFocus value={name} onChange={(event) => setName(event.target.value)} placeholder="Enter player name" required maxLength={60} /></label>
    <div className="form-row"><label className="field"><span>Playing hand</span><select value={hand} onChange={(event) => setHand(event.target.value as Player['hand'])}><option>Right</option><option>Left</option></select></label><label className="field"><span>Grip</span><select value={grip} onChange={(event) => setGrip(event.target.value as Player['grip'])}><option>Shakehand</option><option>Penhold</option></select></label></div>
    <label className="field"><span>Playing style</span><select value={style} onChange={(event) => setStyle(event.target.value)}>{['Attacker', 'Defender', 'All-rounder', 'Counter-attacker', 'Chopper'].map((value) => <option key={value}>{value}</option>)}</select></label>
    <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={!name.trim()}>Add player <ArrowRight size={15} /></button></div>
  </form></Dialog>;
}

function MatchDialog({ players, tournaments, onClose, onCreate }: { players: Player[]; tournaments: Tournament[]; onClose: () => void; onCreate: (input: Pick<Match, 'playerOneId' | 'playerTwoId' | 'format' | 'pointsPerGame' | 'gamesToWin' | 'tournamentId' | 'table'>) => void }) {
  const [one, setOne] = useState(''); const [two, setTwo] = useState(''); const [format, setFormat] = useState('Best of 5'); const [points, setPoints] = useState<11 | 21>(11); const [tournamentId, setTournamentId] = useState(''); const [table, setTable] = useState('Table 01');
  const gamesToWin = format === 'One game' ? 1 : format === 'Best of 3' ? 2 : format === 'Best of 5' ? 3 : 4;
  return <Dialog title="Set up a match" eyebrow="MATCH SETUP" onClose={onClose}><form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (one && two && one !== two) onCreate({ playerOneId: one, playerTwoId: two, format, pointsPerGame: points, gamesToWin, tournamentId: tournamentId || undefined, table }); }}>
    <div className="match-pick-row"><label className="field"><span>Player one</span><select value={one} onChange={(event) => setOne(event.target.value)} required><option value="">Choose player</option>{players.map((player) => <option key={player.id} value={player.id}>{player.name}</option>)}</select></label><span className="versus">VS</span><label className="field"><span>Player two</span><select value={two} onChange={(event) => setTwo(event.target.value)} required><option value="">Choose player</option>{players.map((player) => <option key={player.id} value={player.id}>{player.name}</option>)}</select></label></div>
    <div className="form-row"><label className="field"><span>Match format</span><select value={format} onChange={(event) => setFormat(event.target.value)}>{['One game', 'Best of 3', 'Best of 5', 'Best of 7'].map((value) => <option key={value}>{value}</option>)}</select></label><label className="field"><span>Points per game</span><select value={points} onChange={(event) => setPoints(Number(event.target.value) as 11 | 21)}><option value={11}>11 points · deuce</option><option value={21}>21 points · deuce</option></select></label></div>
    <div className="form-row"><label className="field"><span>Tournament <small>Optional</small></span><select value={tournamentId} onChange={(event) => setTournamentId(event.target.value)}><option value="">Friendly match</option>{tournaments.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="field"><span>Table</span><select value={table} onChange={(event) => setTable(event.target.value)}>{['Table 01', 'Table 02', 'Table 03', 'Table 04'].map((value) => <option key={value}>{value}</option>)}</select></label></div>
    <p className="form-note"><Activity size={15} /> Match settings: win by 2 at deuce. Toss and first server are confirmed on the scoring screen.</p>
    <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={!one || !two || one === two}>Create match <ArrowRight size={15} /></button></div>
  </form></Dialog>;
}

function TournamentDialog({ players, onClose, onCreate }: { players: Player[]; onClose: () => void; onCreate: (input: Pick<Tournament, 'name' | 'format' | 'date' | 'venue' | 'entrantIds'>) => void }) {
  const [name, setName] = useState(''); const [format, setFormat] = useState<Tournament['format']>('Round robin'); const [date, setDate] = useState(new Date().toISOString().slice(0, 10)); const [venue, setVenue] = useState(''); const [entrants, setEntrants] = useState<string[]>([]);
  const toggleEntrant = (id: string) => setEntrants((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  return <Dialog title="Create a tournament" eyebrow="TOURNAMENT SETUP" onClose={onClose} size="wide"><form className="form-stack" noValidate onSubmit={(event) => { event.preventDefault(); if (name.trim() && date && entrants.length >= 2) onCreate({ name: name.trim(), format, date: new Date(`${date}T12:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }), venue, entrantIds: entrants }); }}>
    <div className="form-row"><label className="field"><span>Tournament name</span><input value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Winter Club Open" required maxLength={80} /></label><label className="field"><span>Format</span><select value={format} onChange={(event) => setFormat(event.target.value as Tournament['format'])}><option>Round robin</option><option>Knockout</option></select></label></div>
    <div className="form-row"><label className="field"><span>Start date</span><input type="date" value={date} onChange={(event) => setDate(event.target.value)} required /></label><label className="field"><span>Venue</span><input value={venue} onChange={(event) => setVenue(event.target.value)} placeholder="Add a venue (optional)" maxLength={90} /></label></div>
    <div className="entrant-picker"><div className="entrant-picker-head"><span>Entrants</span><small>{entrants.length} selected · choose at least 2</small></div><div className="entrant-list">{players.map((player) => <label className={`entrant-option ${entrants.includes(player.id) ? 'entrant-option--selected' : ''}`} key={player.id}><input type="checkbox" checked={entrants.includes(player.id)} onChange={() => toggleEntrant(player.id)} /><span className="avatar avatar--tiny">{player.initials}</span><span>{player.name}</span><span className="entrant-rating">{player.rating}</span></label>)}</div></div>
    <p className="form-note"><ClipboardList size={15} /> Draws can be reviewed and edited by the organiser after setup.</p>
    <div className="dialog-actions"><button className="button button-quiet" type="button" onClick={onClose}>Cancel</button><button className="button button-primary" type="submit" disabled={!name.trim() || !date || entrants.length < 2}>Create tournament <ArrowRight size={15} /></button></div>
  </form></Dialog>;
}
