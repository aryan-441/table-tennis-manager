export type PageId = 'overview' | 'matches' | 'tournaments' | 'players' | 'statistics' | 'exports' | 'settings' | 'about';
export type MatchStatus = 'In progress' | 'Scheduled' | 'Completed' | 'Postponed';

export type Player = {
  id: string;
  name: string;
  initials: string;
  hand: 'Right' | 'Left';
  grip: 'Shakehand' | 'Penhold';
  style: string;
  rating: number;
  wins: number;
  losses: number;
  pointsWon: number;
  recent: ('W' | 'L')[];
};

export type PointEvent = { id: string; winnerId: string; score: string; time: string; kind: 'Point' | 'Fault' | 'Let' | 'Correction' };

export type Match = {
  id: string;
  playerOneId: string;
  playerTwoId: string;
  status: MatchStatus;
  tournamentId?: string;
  tournamentName?: string;
  round?: string;
  table?: string;
  startsAt: string;
  format: string;
  pointsPerGame: 11 | 21;
  gamesToWin: number;
  gamesWon: Record<string, number>;
  score: Record<string, number>;
  serverId: string;
  tossWinnerId: string;
  events: PointEvent[];
  winnerId?: string;
  gameResults?: { one: number; two: number; winnerId: string }[];
};

export type Standing = { playerId: string; played: number; wins: number; losses: number; gamesWon: number; gamesLost: number; pointsFor: number; pointsAgainst: number };

export type Tournament = {
  id: string;
  name: string;
  format: 'Round robin' | 'Knockout';
  status: 'Running' | 'Upcoming' | 'Completed' | 'Paused';
  date: string;
  venue: string;
  entrantIds: string[];
  byePlayerIds?: string[];
  matchIds: string[];
  rounds: number;
  completed: number;
  progressPaused: boolean;
  tieBreaks: string[];
  standings: Standing[];
  audit: { id: string; action: string; target: string; reason: string; at: string }[];
};

export type Workspace = { clubName?: string; players: Player[]; matches: Match[]; tournaments: Tournament[] };
