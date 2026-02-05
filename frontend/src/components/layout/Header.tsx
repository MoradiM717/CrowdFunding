import { Link } from 'react-router-dom'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { Button } from '@/components/ui/button'
import { Rocket, BarChart3, PlusCircle, Menu, X } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'
import { useState } from 'react'

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        <Link to="/" className="flex items-center space-x-2">
          <Rocket className="h-6 w-6 text-primary" />
          <span className="font-bold text-xl">CrowdFund</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="mx-6 hidden md:flex items-center space-x-4 lg:space-x-6">
          <Link
            to="/campaigns"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Campaigns
          </Link>
          <Link
            to="/stats"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            <span className="flex items-center gap-1">
              <BarChart3 className="h-4 w-4" />
              Stats
            </span>
          </Link>
        </nav>

        <div className="ml-auto flex items-center space-x-2 md:space-x-4">
          <ThemeToggle />

          <Button asChild variant="outline" size="sm" className="hidden sm:flex">
            <Link to="/create">
              <PlusCircle className="mr-2 h-4 w-4" />
              Create Campaign
            </Link>
          </Button>

          <div className="hidden sm:block">
            <ConnectButton
              showBalance={false}
              chainStatus="icon"
              accountStatus={{
                smallScreen: 'avatar',
                largeScreen: 'full',
              }}
            />
          </div>

          {/* Mobile Menu Button */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t bg-background">
          <nav className="container py-4 space-y-3">
            <Link
              to="/campaigns"
              className="block text-sm font-medium text-muted-foreground hover:text-primary"
              onClick={() => setMobileMenuOpen(false)}
            >
              Campaigns
            </Link>
            <Link
              to="/stats"
              className="block text-sm font-medium text-muted-foreground hover:text-primary"
              onClick={() => setMobileMenuOpen(false)}
            >
              Stats
            </Link>
            <Link
              to="/create"
              className="block text-sm font-medium text-muted-foreground hover:text-primary"
              onClick={() => setMobileMenuOpen(false)}
            >
              Create Campaign
            </Link>
            <div className="pt-2">
              <ConnectButton
                showBalance={false}
                chainStatus="icon"
                accountStatus="full"
              />
            </div>
          </nav>
        </div>
      )}
    </header>
  )
}
