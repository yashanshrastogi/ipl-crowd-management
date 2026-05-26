/**
 * useFirestore — Real-time Firestore snapshot listener hook.
 *
 * Wraps `onSnapshot` for both collections and individual documents.
 * Automatically unsubscribes on component unmount.
 *
 * @example
 *   const { data, loading, error } = useFirestoreCollection('stadiums/chinnaswamy/gates');
 *   const { data, loading, error } = useFirestoreDoc('stadiums/chinnaswamy');
 */

import { useState, useEffect } from 'react';
import {
  collection,
  doc,
  onSnapshot,
  query,
  orderBy,
  limit as fbLimit,
} from 'firebase/firestore';
import { initFirebaseDynamic } from '../services/firebase';

/**
 * Subscribe to a Firestore collection in real time.
 * @param {string} path             Firestore collection path
 * @param {object} opts
 * @param {string} [opts.orderByField]  Field name to order by
 * @param {'asc'|'desc'} [opts.direction]  Order direction
 * @param {number} [opts.limit]     Max documents to return
 * @returns {{ data: Array, loading: boolean, error: Error|null }}
 */
export function useFirestoreCollection(path, opts = {}) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!path) return;

    let unsubscribe = () => {};
    let isMounted = true;

    const setupListener = async () => {
      const db = await initFirebaseDynamic();
      if (!isMounted) return;
      
      if (!db) {
        setError(new Error('Firebase DB not initialized'));
        setLoading(false);
        return;
      }

      const constraints = [];
      if (opts.orderByField) {
        constraints.push(orderBy(opts.orderByField, opts.direction || 'asc'));
      }
      if (opts.limit) {
        constraints.push(fbLimit(opts.limit));
      }

      const q = query(collection(db, path), ...constraints);

      unsubscribe = onSnapshot(
        q,
        (snapshot) => {
          if (!isMounted) return;
          const docs = snapshot.docs.map((d) => ({ id: d.id, ...d.data() }));
          setData(docs);
          setLoading(false);
        },
        (err) => {
          if (!isMounted) return;
          console.error(`Firestore listener error [${path}]:`, err);
          setError(err);
          setLoading(false);
        },
      );
    };

    setupListener();

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [path, opts.orderByField, opts.direction, opts.limit]);

  return { data, loading, error };
}

/**
 * Subscribe to a single Firestore document in real time.
 * @param {string} path  Firestore document path (e.g. 'stadiums/chinnaswamy')
 * @returns {{ data: object|null, loading: boolean, error: Error|null }}
 */
export function useFirestoreDoc(path) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!path) return;

    let unsubscribe = () => {};
    let isMounted = true;

    const setupListener = async () => {
      const db = await initFirebaseDynamic();
      if (!isMounted) return;

      if (!db) {
        setError(new Error('Firebase DB not initialized'));
        setLoading(false);
        return;
      }

      unsubscribe = onSnapshot(
        doc(db, path),
        (snapshot) => {
          if (!isMounted) return;
          if (snapshot.exists()) {
            setData({ id: snapshot.id, ...snapshot.data() });
          } else {
            setData(null);
          }
          setLoading(false);
        },
        (err) => {
          if (!isMounted) return;
          console.error(`Firestore doc listener error [${path}]:`, err);
          setError(err);
          setLoading(false);
        },
      );
    };

    setupListener();

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [path]);

  return { data, loading, error };
}

export default useFirestoreCollection;
