<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="1050" height="560" viewBox="0 0 1050 560"
     role="img" aria-labelledby="title desc">
  <title id="title">{{TITLE}}</title>
  <desc id="desc">{{DESC}}</desc>

  <style>
    text {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
                   "Liberation Mono", "Courier New", monospace;
      white-space: pre;
    }
    .body { fill: {{TEXT}}; font-size: 15px; }
    .muted { fill: {{MUTED}}; }
    .key { fill: {{KEY}}; }
    .value { fill: {{VALUE}}; }
    .green { fill: {{GREEN}}; }
    .portrait { fill: {{PORTRAIT}}; font-size: 10.4px; letter-spacing: -0.45px; }
    .outline {
      fill: none;
      stroke: {{LINE}};
      stroke-width: 1.45;
      stroke-linecap: round;
      stroke-linejoin: round;
      opacity: .88;
    }
    .feature {
      fill: none;
      stroke: {{TEXT}};
      stroke-width: 1.75;
      stroke-linecap: round;
      stroke-linejoin: round;
      opacity: .95;
    }
    .feature-dot { fill: {{TEXT}}; opacity: .92; }
  </style>

  <rect x="1" y="1" width="1048" height="558" rx="18"
        fill="{{BG}}" stroke="{{BORDER}}" stroke-width="2"/>
  <rect x="14" y="14" width="374" height="532" rx="14"
        fill="{{BG}}" stroke="{{GLOW}}" stroke-width="1" opacity=".55"/>

  <text class="portrait">
{{PORTRAIT_TSPANS}}
  </text>

{{PORTRAIT_PATHS}}

  <line x1="405" y1="36" x2="1025" y2="36"
        stroke="{{BORDER}}" stroke-width="1.2"/>

  <text class="body">
{{RIGHT_TEXT}}
  </text>
</svg>
