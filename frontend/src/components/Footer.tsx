import { APP_VERSION } from "@/lib/version";
import logo from "@/assets/logo.png";

export function Footer() {
  return (
    <footer className="border-t py-6 mt-12">
      <div className="container flex flex-col items-center gap-3 text-sm text-muted-foreground sm:flex-row sm:justify-between">
        <div className="flex items-center gap-2">
          <img src={logo} alt="SeeWhozThere" className="h-5 w-5 rounded" />
          <span className="font-medium">SeeWhozThere</span>
          <span className="text-xs opacity-60">v{APP_VERSION}</span>
        </div>
        <p className="text-center">
          A product by{" "}
          <a
            href="https://ai-focus.org"
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-primary hover:underline"
          >
            TechSilon Solutions
          </a>
        </p>
        <p className="text-center text-xs opacity-70">
          Crafted by <span className="font-medium text-foreground/80">Sujit</span>
        </p>
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-foreground transition-colors"
        >
          GitHub
        </a>
      </div>
    </footer>
  );
}
