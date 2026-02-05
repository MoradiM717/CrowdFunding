import { Link } from 'react-router-dom'
import { Rocket, Github, Twitter } from 'lucide-react'

export function Footer() {
  return (
    <footer className="border-t bg-background">
      <div className="container py-8 md:py-12">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="flex items-center space-x-2">
              <Rocket className="h-6 w-6 text-primary" />
              <span className="font-bold text-xl">CrowdFund</span>
            </Link>
            <p className="mt-4 text-sm text-muted-foreground">
              Decentralized crowdfunding platform built on Ethereum.
              Fund your dreams, support innovation.
            </p>
          </div>

          <div>
            <h3 className="font-semibold mb-4">Platform</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <Link to="/campaigns" className="hover:text-primary">
                  Browse Campaigns
                </Link>
              </li>
              <li>
                <Link to="/create" className="hover:text-primary">
                  Start a Campaign
                </Link>
              </li>
              <li>
                <Link to="/stats" className="hover:text-primary">
                  Statistics
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-4">Resources</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <a href="/docs" className="hover:text-primary">
                  API Documentation
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-primary">
                  How It Works
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-primary">
                  FAQ
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h3 className="font-semibold mb-4">Connect</h3>
            <div className="flex space-x-4">
              <a
                href="#"
                className="text-muted-foreground hover:text-primary"
                aria-label="GitHub"
              >
                <Github className="h-5 w-5" />
              </a>
              <a
                href="#"
                className="text-muted-foreground hover:text-primary"
                aria-label="Twitter"
              >
                <Twitter className="h-5 w-5" />
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 border-t pt-8 text-center text-sm text-muted-foreground">
          <p>&copy; {new Date().getFullYear()} CrowdFund. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
