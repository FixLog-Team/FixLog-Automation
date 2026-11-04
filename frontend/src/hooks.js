import { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 3000;

/** 서버 조회 훅. 데이터와 로딩·오류 상태를 함께 돌려주고, pollWhile이 참이면 주기적으로 다시 조회한다. */
export function useServerData(fetcher, deps = [], { pollWhile } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(async () => {
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  const shouldPoll = pollWhile ? pollWhile(data) : false;
  useEffect(() => {
    if (!shouldPoll) return undefined;
    const timer = setInterval(reload, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [shouldPoll, reload]);

  return { data, error, isLoading, reload };
}
