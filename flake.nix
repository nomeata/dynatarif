{
  description = "Energy price scraper for web.dynatarif.de";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python312.withPackages (ps: [ ps.playwright ]);
    in
    {
      devShells.${system}.default = pkgs.mkShell {
        packages = [ python ];
        env.PLAYWRIGHT_BROWSERS_PATH = "${pkgs.playwright-driver.browsers}";
        env.PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = "true";
      };
    };
}
