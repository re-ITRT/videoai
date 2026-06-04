import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import AuthGuard from './components/AuthGuard'
import Login from './pages/login'
import Register from './pages/register'
import Dashboard from './pages/dashboard'
import Reference from './pages/reference'
import Templates from './pages/templates'
import MaterialList from './modules/material/index'
import MaterialUpload from './modules/material/upload'
import ScriptList from './modules/script/index'
import ScriptGenerate from './modules/script/generate'
import ScriptDetail from './modules/script/detail'
import Profile from './pages/profile'
import AdminUsers from './pages/admin/users'
import Attribution from './pages/attribution'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<AuthGuard><Layout /></AuthGuard>}>
          <Route index element={<Dashboard />} />
          <Route path="reference" element={<Reference />} />
          <Route path="templates" element={<Templates />} />
          <Route path="material" element={<MaterialList />} />
          <Route path="material/upload" element={<MaterialUpload />} />
          <Route path="script" element={<ScriptList />} />
          <Route path="script/generate" element={<ScriptGenerate />} />
          <Route path="script/:id" element={<ScriptDetail />} />
          <Route path="profile" element={<Profile />} />
          <Route path="admin/users" element={<AdminUsers />} />
          <Route path="attribution" element={<Attribution />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
