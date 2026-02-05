import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { WagmiProvider } from 'wagmi'
import { RainbowKitProvider, darkTheme, lightTheme } from '@rainbow-me/rainbowkit'
import '@rainbow-me/rainbowkit/styles.css'

import { config } from '@/lib/wagmi'
import { Layout } from '@/components/layout/Layout'
import { ErrorBoundary } from '@/components/common/ErrorBoundary'
import { Home } from '@/pages/Home'
import { Campaigns } from '@/pages/Campaigns'
import { CampaignDetail } from '@/pages/CampaignDetail'
import { CreateCampaign } from '@/pages/CreateCampaign'
import { Profile } from '@/pages/Profile'
import { Stats } from '@/pages/Stats'
import { NotFound } from '@/pages/NotFound'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <WagmiProvider config={config}>
        <QueryClientProvider client={queryClient}>
          <RainbowKitProvider
            theme={{
              lightMode: lightTheme({
                accentColor: '#3b82f6',
                accentColorForeground: 'white',
                borderRadius: 'medium',
              }),
              darkMode: darkTheme({
                accentColor: '#3b82f6',
                accentColorForeground: 'white',
                borderRadius: 'medium',
              }),
            }}
          >
            <BrowserRouter>
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<Home />} />
                  <Route path="campaigns" element={<Campaigns />} />
                  <Route path="campaign/:address" element={<CampaignDetail />} />
                  <Route path="create" element={<CreateCampaign />} />
                  <Route path="profile" element={<Profile />} />
                  <Route path="profile/:address" element={<Profile />} />
                  <Route path="stats" element={<Stats />} />
                  <Route path="*" element={<NotFound />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </RainbowKitProvider>
        </QueryClientProvider>
      </WagmiProvider>
    </ErrorBoundary>
  )
}

export default App
