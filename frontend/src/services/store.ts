import { initialWorkspace } from '../data/seed';
import type { Match, Player, Tournament, Workspace } from '../types';

const STORAGE_KEY = 'rallydesk-workspace-v2';

export function loadWorkspace(): Workspace {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return structuredClone(initialWorkspace);
    const parsed = JSON.parse(saved) as Workspace;
    if (!parsed.players || !parsed.matches || !parsed.tournaments) return structuredClone(initialWorkspace);
    return parsed;
  } catch {
    return structuredClone(initialWorkspace);
  }
}

export function saveWorkspace(workspace: Workspace): boolean {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
    return true;
  } catch {
    return false;
  }
}

export function resetWorkspace() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* Save effect reports storage failures to the organiser. */ }
  return structuredClone(initialWorkspace);
}

export function createPlayer(name: string, hand: Player['hand'], grip: Player['grip'], style: string): Player {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]?.toUpperCase() ?? '').join('');
  return { id: crypto.randomUUID(), name: name.trim(), initials, hand, grip, style, rating: 1000, wins: 0, losses: 0, pointsWon: 0, recent: [] };
}

export function createMatch(input: Pick<Match, 'playerOneId' | 'playerTwoId' | 'format' | 'pointsPerGame' | 'gamesToWin' | 'tournamentId' | 'table'>, players: Player[]): Match {
  const server = players.find((player) => player.id === input.playerOneId);
  if (!server) throw new Error('Choose two saved players before creating a match.');
  return { ...input, id: crypto.randomUUID(), status: 'Scheduled', startsAt: 'Now', gamesWon: { [input.playerOneId]: 0, [input.playerTwoId]: 0 }, score: { [input.playerOneId]: 0, [input.playerTwoId]: 0 }, serverId: server.id, tossWinnerId: server.id, events: [], tournamentName: undefined };
}

export function createTournament(input: Pick<Tournament, 'name' | 'format' | 'date' | 'venue' | 'entrantIds'>): Tournament {
  const entrantCount = input.entrantIds.length;
  const rounds = input.format === 'Knockout' ? Math.ceil(Math.log2(Math.max(2, entrantCount))) : Math.max(1, entrantCount % 2 ? entrantCount : entrantCount - 1);
  const bracketSize = 2 ** Math.ceil(Math.log2(Math.max(2, entrantCount)));
  const byePlayerIds = input.format === 'Knockout' ? input.entrantIds.slice(0, bracketSize - entrantCount) : [];
  return { ...input, id: crypto.randomUUID(), status: 'Upcoming', byePlayerIds, matchIds: [], rounds, completed: 0, progressPaused: false, tieBreaks: input.format === 'Round robin' ? ['Match wins', 'Game difference', 'Games won'] : [], standings: input.entrantIds.map((playerId) => ({ playerId, played: 0, wins: 0, losses: 0, gamesWon: 0, gamesLost: 0, pointsFor: 0, pointsAgainst: 0 })), audit: [] };
}



export function generateTournamentFixtures(tournament: Tournament, players: Player[]): Match[] {
  const entrants = tournament.entrantIds.filter((id) => players.some((player) => player.id === id));
  const fixtures: Match[] = [];
  const addFixture = (one: string, two: string, round: string) => {
    const match: Match = {
      id: crypto.randomUUID(), playerOneId: one, playerTwoId: two, status: 'Scheduled',
      tournamentId: tournament.id, tournamentName: tournament.name, round, startsAt: 'TBD',
      format: 'Best of 5', pointsPerGame: 11, gamesToWin: 3,
      gamesWon: { [one]: 0, [two]: 0 }, score: { [one]: 0, [two]: 0 },
      serverId: one, tossWinnerId: one, events: [],
    };
    fixtures.push(match);
  };
  if (tournament.format === 'Round robin') {
    const rotation: (string | null)[] = [...entrants];
    if (rotation.length % 2) rotation.push(null);
    for (let round = 0; round < rotation.length - 1; round += 1) {
      for (let index = 0; index < rotation.length / 2; index += 1) {
        let one = rotation[index]; let two = rotation[rotation.length - 1 - index];
        if (round % 2 && index === 0) [one, two] = [two, one];
        if (one && two) addFixture(one, two, `Round ${round + 1}`);
      }
      const fixed = rotation[0];
      const moved = rotation.pop();
      if (moved !== undefined) rotation.splice(1, 0, moved);
      rotation[0] = fixed;
    }
  } else {
    const byeIds = tournament.byePlayerIds ?? [];
    const firstRound = entrants.filter((id) => !byeIds.includes(id));
    for (let index = 0; index + 1 < firstRound.length; index += 2) addFixture(firstRound[index], firstRound[index + 1], 'Round 1');
  }
  return fixtures;
}


export function generateKnockoutRoundFixtures(tournament: Tournament, entrantIds: string[], roundNumber: number): Match[] {
  const matches: Match[] = [];
  for (let index = 0; index + 1 < entrantIds.length; index += 2) {
    const one = entrantIds[index]; const two = entrantIds[index + 1];
    matches.push({ id: crypto.randomUUID(), playerOneId: one, playerTwoId: two, status: 'Scheduled', tournamentId: tournament.id, tournamentName: tournament.name, round: `Round ${roundNumber}`, startsAt: 'TBD', format: 'Best of 5', pointsPerGame: 11, gamesToWin: 3, gamesWon: { [one]: 0, [two]: 0 }, score: { [one]: 0, [two]: 0 }, serverId: one, tossWinnerId: one, events: [] });
  }
  return matches;
}
