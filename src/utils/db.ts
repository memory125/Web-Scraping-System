import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface CrawlerDB extends DBSchema {
  targets: {
    key: string;
    value: {
      id: string;
      url: string;
      status: string;
      result?: any;
      error?: string;
      parentUrl?: string;
      depth?: number;
      createdAt: string;
      updatedAt: string;
    };
    indexes: { 'by-status': string; 'by-url': string };
  };
  history: {
    key: string;
    value: {
      id: string;
      name: string;
      timestamp: string;
      targets: any[];
      totalUrls: number;
      successCount: number;
      failedCount: number;
    };
    indexes: { 'by-timestamp': string };
  };
  settings: {
    key: string;
    value: {
      id: string;
      settings: any;
      updatedAt: string;
    };
  };
}

const DB_NAME = 'crawler-db';
const DB_VERSION = 1;

let db: IDBPDatabase<CrawlerDB> | null = null;

export async function initDB(): Promise<IDBPDatabase<CrawlerDB>> {
  if (db) return db;
  
  db = await openDB<CrawlerDB>(DB_NAME, DB_VERSION, {
    upgrade(database) {
      const targetStore = database.createObjectStore('targets', { keyPath: 'id' });
      targetStore.createIndex('by-status', 'status');
      targetStore.createIndex('by-url', 'url');
      
      const historyStore = database.createObjectStore('history', { keyPath: 'id' });
      historyStore.createIndex('by-timestamp', 'timestamp');
      
      database.createObjectStore('settings', { keyPath: 'id' });
    },
  });
  
  return db;
}

export async function saveTargets(targets: any[]): Promise<void> {
  const database = await initDB();
  const tx = database.transaction('targets', 'readwrite');
  await tx.store.clear();
  for (const target of targets) {
    await tx.store.put({ ...target, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() });
  }
  await tx.done;
}

export async function loadTargets(): Promise<any[]> {
  const database = await initDB();
  return database.getAll('targets');
}

export async function saveHistory(history: any[]): Promise<void> {
  const database = await initDB();
  const tx = database.transaction('history', 'readwrite');
  await tx.store.clear();
  for (const record of history) {
    await tx.store.put(record);
  }
  await tx.done;
}

export async function loadHistory(): Promise<any[]> {
  const database = await initDB();
  return database.getAll('history');
}

export async function saveSettings(settings: any): Promise<void> {
  const database = await initDB();
  await database.put('settings', { id: 'main', settings, updatedAt: new Date().toISOString() });
}

export async function loadSettings(): Promise<any | null> {
  const database = await initDB();
  const result = await database.get('settings', 'main');
  return result?.settings || null;
}

export async function clearAllData(): Promise<void> {
  const database = await initDB();
  await database.clear('targets');
  await database.clear('history');
}
