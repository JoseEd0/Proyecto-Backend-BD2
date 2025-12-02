import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import Layout from "./components/Layout";
import SQLConsole from "./pages/SQLConsole";
import SIFTManager from "./pages/SIFTManager";
import BoWManager from "./pages/BoWManager";
import AudioManager from "./pages/AudioManager";
import TablesView from "./pages/TablesView";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/sql" replace />} />
          <Route path="sql" element={<SQLConsole />} />
          <Route path="sift" element={<SIFTManager />} />
          <Route path="bow" element={<BoWManager />} />
          <Route path="audio" element={<AudioManager />} />
          <Route path="tables" element={<TablesView />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
