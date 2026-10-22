import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Login } from './pages/Login'
import { HomePage } from './pages/runtime/HomePage'
import { ThreadsPage } from './pages/runtime/ThreadsPage'
import { QuotesPage } from './pages/runtime/QuotesPage'
import { CustomersPage } from './pages/runtime/CustomersPage'
import { PositioningPage } from './pages/runtime/PositioningPage'
import { IntelPage } from './pages/runtime/IntelPage'
import { ProcurementPage } from './pages/runtime/ProcurementPage'
import { SocialPage } from './pages/runtime/SocialPage'
import { SocialCallbackPage } from './pages/runtime/SocialCallbackPage'
import { EventsPage } from './pages/runtime/EventsPage'
import { ReportsPage } from './pages/runtime/ReportsPage'
import { ConnectPage } from './pages/setup/ConnectPage'
import { CatalogPage } from './pages/setup/CatalogPage'
import { KnowledgePage } from './pages/setup/KnowledgePage'
import { PricingPage } from './pages/setup/PricingPage'
import { VoicePage } from './pages/setup/VoicePage'
import { GoLivePage } from './pages/setup/GoLivePage'
import { LicensePage } from './pages/setup/LicensePage'

function Shell() {
  const { token } = useAuth()
  if (!token) return <Login />
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/inbox" element={<ThreadsPage />} />
        <Route path="/quotes" element={<QuotesPage />} />
        <Route path="/customers" element={<CustomersPage />} />
        <Route path="/social" element={<SocialPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/positioning" element={<PositioningPage />} />
        <Route path="/intel" element={<IntelPage />} />
        <Route path="/procurement" element={<ProcurementPage />} />
        <Route path="/connect" element={<ConnectPage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/voice" element={<VoicePage />} />
        <Route path="/go-live" element={<GoLivePage />} />
        <Route path="/license" element={<LicensePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* OAuth callback landing — must work even without a console token */}
          <Route path="/integrations/social/:provider" element={<SocialCallbackPage />} />
          <Route path="/*" element={<Shell />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
