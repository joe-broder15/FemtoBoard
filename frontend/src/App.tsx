import { Route, Routes } from "react-router-dom";
import BoardIndex from "./pages/BoardIndex";
import BoardCatalog from "./pages/BoardCatalog";
import ThreadView from "./pages/ThreadView";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<BoardIndex />} />
      <Route path="/thread/:id" element={<ThreadView />} />
      <Route path="/:slug" element={<BoardCatalog />} />
    </Routes>
  );
}
