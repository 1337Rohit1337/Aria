import React, { useEffect } from 'react';
import { useAriaStore } from './store/useAriaStore';
import { Layout } from './components/Layout';

export const App: React.FC = () => {
  const { fetchSessions, isDarkMode } = useAriaStore();

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    fetchSessions();
  }, []);

  return <Layout />;
};

export default App;