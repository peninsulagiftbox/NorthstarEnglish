let database: Promise<IDBDatabase> | null = null;
function open() {
  if (!database) database = new Promise((resolve, reject) => {
    const request = indexedDB.open('northstar-learning-v1', 1);
    request.onupgradeneeded = () => { for (const store of ['drafts', 'outbox', 'exposure']) request.result.createObjectStore(store); };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => { database = null; reject(request.error); };
    request.onblocked = () => { database = null; reject(new Error('本机存储升级被另一页面阻塞')); };
  });
  return database;
}
export async function read<T>(store: string, key: string): Promise<T | undefined> {
  const db = await open(); return new Promise((resolve, reject) => {
    const request = db.transaction(store).objectStore(store).get(key);
    request.onsuccess = () => resolve(request.result as T | undefined); request.onerror = () => reject(request.error);
  });
}
export async function write(store: string, key: string, value: unknown, onlyNew = false) {
  const db = await open(); return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite'); if (onlyNew) tx.objectStore(store).add(value, key); else tx.objectStore(store).put(value, key);
    tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
  });
}
export async function remove(store: string, key: string, expectedEventId?: string) {
  const db = await open(); return new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    if (expectedEventId) {
      const request = tx.objectStore(store).get(key);
      request.onsuccess = () => { if (request.result?.eventId === expectedEventId) tx.objectStore(store).delete(key); };
    } else tx.objectStore(store).delete(key);
    tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error);
  });
}
