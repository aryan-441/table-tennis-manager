import type { Workspace } from '../types';

// Every workspace starts empty so organisers create their own club records.
export const initialWorkspace: Workspace = {
  clubName: '',
  players: [],
  matches: [],
  tournaments: [],
};
