import { APP_VERSION, BUILD_DATE, BUILD_NUMBER } from "@/lib/version";
import logo from "@/assets/logo.png";

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t bg-card/50 backdrop-blur-sm py-5 mt-12">
      <div className="container">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm text-muted-foreground">

          {/* Left: Branding */}
          <div className="flex items-center gap-2">
            <img src={logo} alt="SeeWhozThere" className="h-6 w-6 object-contain" />
            <div className="flex flex-col leading-tight">
              <span className="font-semibold text-foreground/90 text-sm">SeeWhozThere</span>
              <span className="text-xs opacity-60">Smart Home Security</span>
            </div>
          </div>

          {/* Center: Creator */}
          <div className="text-center text-xs">
            <p>
              Designed &amp; Created by{" "}
              <span className="font-semibold text-foreground/80">Sujit G</span>
            </p>
            <p>
              &copy; {year}{" "}
              <a
                href="https://techsilon.com"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-primary hover:underline"
              >
                Techsilon
              </a>
              {" "}· All rights reserved
            </p>
          </div>

          {/* Right: Version */}
          <div className="text-right text-xs opacity-70 font-mono">
            <p>v{APP_VERSION} · Build {BUILD_NUMBER}</p>
            <p>{BUILD_DATE}</p>
          </div>

        </div>
      </div>
    </footer>
  );
}
