import React, { createContext, useContext, useState } from 'react';

const SimulationContext = createContext();

export const SimulationProvider = ({ children }) => {
  const [isAttacked, setIsAttacked] = useState(false);
  const [noiseLevel, setNoiseLevel] = useState(0.05);
  const [autoMitigate, setAutoMitigate] = useState(false);
  const [activeProtocol, setActiveProtocol] = useState('BB84');

  return (
    <SimulationContext.Provider value={{
      isAttacked, setIsAttacked,
      noiseLevel, setNoiseLevel,
      autoMitigate, setAutoMitigate,
      activeProtocol, setActiveProtocol
    }}>
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => {
  const context = useContext(SimulationContext);
  if (context === undefined) {
    throw new Error('useSimulation must be used within a SimulationProvider');
  }
  return context;
};
