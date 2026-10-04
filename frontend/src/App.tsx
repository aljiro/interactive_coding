import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { Home } from './pages/Home';
import { Projector } from './pages/Projector';
import { Student } from './pages/Student';
import { Teacher } from './pages/Teacher';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/join/:code" element={<Home />} />
        <Route path="/student" element={<Student />} />
        <Route path="/teacher" element={<Teacher />} />
        <Route path="/live/:sessionId" element={<Projector />} />
        <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
