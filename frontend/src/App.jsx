import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './views/Home';
import SimView from './views/SimView';
import MLAnalysis from './views/MLAnalysis';
import ConceptsLibrary from './views/ConceptsLibrary';
import History from './views/History';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="sim" element={<SimView />} />
        <Route path="ml" element={<MLAnalysis />} />
        <Route path="concepts" element={<ConceptsLibrary />} />
        <Route path="history" element={<History />} />
      </Route>
    </Routes>
  );
}

export default App;
