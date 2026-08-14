/**
 * WayLens : Enhanced High-Definition Interactive Floor Map
 * Supports High-DPI canvas, smooth animated path particles, radar sweep user pointer,
 * distinct facility icons, and interactive floor transitions.
 */

(function() {
  const NODE_COORDS = {
    // === FLOOR 5 (Ground Floor) ===
    'Steps_5SW': {x:120, y:430, floor:5, type:'steps', label:'Stairs SW'},
    'Lift_5C': {x:165, y:440, floor:5, type:'lift', label:'Lift C'},
    '501': {x:215, y:440, floor:5, type:'room', label:'501'},
    '502': {x:280, y:440, floor:5, type:'room', label:'502'},
    '503': {x:345, y:440, floor:5, type:'room', label:'503'},
    '504': {x:415, y:440, floor:5, type:'room', label:'504'},
    'Steps_5SE': {x:475, y:440, floor:5, type:'steps', label:'Stairs SE'},
    'Gate_5E': {x:540, y:440, floor:5, type:'gate', label:'East Gate'},
    'Xerox_5': {x:95, y:465, floor:5, type:'landmark', label:'Xerox'},
    'Physics_Lab': {x:95, y:490, floor:5, type:'landmark', label:'Physics Lab'},
    'Small_Gate_5': {x:75, y:510, floor:5, type:'gate', label:'Gate'},
    'Gents_Toilet_5E': {x:510, y:150, floor:5, type:'toilet', label:'Gents WC'},
    'Ladies_Toilet_5E': {x:510, y:190, floor:5, type:'toilet', label:'Ladies WC'},
    '507A': {x:510, y:235, floor:5, type:'room', label:'507A'},
    '507': {x:510, y:280, floor:5, type:'room', label:'507'},
    '506': {x:510, y:330, floor:5, type:'room', label:'506'},
    '505': {x:510, y:380, floor:5, type:'room', label:'505'},
    '513': {x:95, y:395, floor:5, type:'room', label:'513'},
    '514': {x:95, y:365, floor:5, type:'room', label:'514'},
    '515': {x:95, y:335, floor:5, type:'room', label:'515'},
    '516': {x:95, y:305, floor:5, type:'room', label:'516'},
    '517': {x:95, y:275, floor:5, type:'room', label:'517'},
    '518': {x:95, y:245, floor:5, type:'room', label:'518'},
    'Ladies_Toilet_5W': {x:95, y:215, floor:5, type:'toilet', label:'Ladies WC'},
    'Gents_Toilet_5W': {x:95, y:185, floor:5, type:'toilet', label:'Gents WC'},
    '521': {x:95, y:155, floor:5, type:'room', label:'521'},
    '522': {x:95, y:125, floor:5, type:'room', label:'522'},
    'Water_5': {x:95, y:80, floor:5, type:'toilet', label:'Water'},
    'Hall_5': {x:155, y:80, floor:5, type:'landmark', label:'Hall 5'},
    'Seminar_Hall': {x:225, y:80, floor:5, type:'landmark', label:'Seminar Hall'},
    'Panel_Room': {x:225, y:115, floor:5, type:'landmark', label:'Panel Room'},
    '526': {x:300, y:80, floor:5, type:'room', label:'526'},
    '527': {x:370, y:80, floor:5, type:'room', label:'527'},
    'Dept_of_Commerce': {x:440, y:80, floor:5, type:'landmark', label:'Commerce Dept'},
    'Lift_5NE': {x:525, y:80, floor:5, type:'lift', label:'Lift NE'},
    '523': {x:300, y:120, floor:5, type:'room', label:'523'},
    '524': {x:370, y:120, floor:5, type:'room', label:'524'},
    'Steps_5NE': {x:450, y:120, floor:5, type:'steps', label:'Stairs NE'},
    'Gate_5NE': {x:525, y:120, floor:5, type:'gate', label:'NE Gate'},

    // === FLOOR 6 (First Floor) ===
    'Lift_6C': {x:165, y:440, floor:6, type:'lift', label:'Lift C'},
    '601': {x:215, y:440, floor:6, type:'room', label:'601'},
    'Quantum_Computing': {x:270, y:440, floor:6, type:'landmark', label:'Quantum Lab'},
    '602': {x:335, y:440, floor:6, type:'room', label:'602'},
    '603': {x:400, y:440, floor:6, type:'room', label:'603'},
    'Steps_6E': {x:475, y:440, floor:6, type:'steps', label:'Stairs E'},
    'Gents_Toilet_6E': {x:510, y:150, floor:6, type:'toilet', label:'Gents WC'},
    'Ladies_Toilet_6E': {x:510, y:190, floor:6, type:'toilet', label:'Ladies WC'},
    '607A': {x:510, y:235, floor:6, type:'room', label:'607A'},
    '607': {x:510, y:275, floor:6, type:'room', label:'607'},
    '606': {x:510, y:315, floor:6, type:'room', label:'606'},
    '605': {x:510, y:355, floor:6, type:'room', label:'605'},
    '604': {x:510, y:395, floor:6, type:'room', label:'604'},
    '613': {x:95, y:400, floor:6, type:'room', label:'613'},
    'Dept_of_Math': {x:95, y:370, floor:6, type:'landmark', label:'Math Dept'},
    '615': {x:95, y:340, floor:6, type:'room', label:'615'},
    '616': {x:95, y:310, floor:6, type:'room', label:'616'},
    '617': {x:95, y:280, floor:6, type:'room', label:'617'},
    'Energy_Science_Lab': {x:95, y:250, floor:6, type:'landmark', label:'Energy Lab'},
    'Ladies_Toilet_6W': {x:95, y:220, floor:6, type:'toilet', label:'Ladies WC'},
    'Gents_Toilet_6W': {x:95, y:190, floor:6, type:'toilet', label:'Gents WC'},
    '621': {x:95, y:160, floor:6, type:'room', label:'621'},
    'Dept_of_CS_W': {x:95, y:125, floor:6, type:'landmark', label:'CS Dept W'},
    'Water_6': {x:95, y:80, floor:6, type:'toilet', label:'Water'},
    '625': {x:200, y:80, floor:6, type:'room', label:'625'},
    '626': {x:290, y:80, floor:6, type:'room', label:'626'},
    '627': {x:370, y:80, floor:6, type:'room', label:'627'},
    'Dept_of_CS_N': {x:440, y:80, floor:6, type:'landmark', label:'CS Dept N'},
    'Lift_6NE': {x:525, y:80, floor:6, type:'lift', label:'Lift NE'},
    '623': {x:290, y:120, floor:6, type:'room', label:'623'},
    '624': {x:370, y:120, floor:6, type:'room', label:'624'},
    'Steps_6NE': {x:450, y:120, floor:6, type:'steps', label:'Stairs NE'},

    // === FLOOR 7 (Second Floor) ===
    'Lift_7C': {x:165, y:440, floor:7, type:'lift', label:'Lift C'},
    '701': {x:215, y:440, floor:7, type:'room', label:'701'},
    '702': {x:280, y:440, floor:7, type:'room', label:'702'},
    '703': {x:350, y:440, floor:7, type:'room', label:'703'},
    '704': {x:415, y:440, floor:7, type:'room', label:'704'},
    'Steps_7E': {x:475, y:440, floor:7, type:'steps', label:'Stairs E'},
    'Gents_Toilet_7E': {x:510, y:150, floor:7, type:'toilet', label:'Gents WC'},
    'Ladies_Toilet_7E': {x:510, y:190, floor:7, type:'toilet', label:'Ladies WC'},
    '709C': {x:510, y:235, floor:7, type:'room', label:'709C'},
    '708': {x:510, y:280, floor:7, type:'room', label:'708'},
    '707': {x:510, y:325, floor:7, type:'room', label:'707'},
    '705': {x:510, y:380, floor:7, type:'room', label:'705'},
    '710': {x:95, y:400, floor:7, type:'room', label:'710'},
    '711': {x:95, y:375, floor:7, type:'room', label:'711'},
    '713': {x:95, y:350, floor:7, type:'room', label:'713'},
    '714': {x:95, y:325, floor:7, type:'room', label:'714'},
    '715': {x:95, y:300, floor:7, type:'room', label:'715'},
    'Dept_of_Psychology': {x:60, y:300, floor:7, type:'landmark', label:'Psychology'},
    '716': {x:95, y:275, floor:7, type:'room', label:'716'},
    '717': {x:95, y:250, floor:7, type:'room', label:'717'},
    '718': {x:95, y:225, floor:7, type:'room', label:'718'},
    'Ladies_Toilet_7W': {x:95, y:200, floor:7, type:'toilet', label:'Ladies WC'},
    'Gents_Toilet_7W': {x:95, y:175, floor:7, type:'toilet', label:'Gents WC'},
    '722': {x:95, y:150, floor:7, type:'room', label:'722'},
    '721': {x:95, y:80, floor:7, type:'room', label:'721'},
    'Prayer_Hall': {x:165, y:80, floor:7, type:'landmark', label:'Prayer Hall'},
    'Assembly_Hall': {x:240, y:80, floor:7, type:'landmark', label:'Assembly Hall'},
    '725': {x:310, y:80, floor:7, type:'room', label:'725'},
    '724': {x:310, y:120, floor:7, type:'room', label:'724'},
    '727': {x:380, y:80, floor:7, type:'room', label:'727'},
    'School_of_Education': {x:450, y:80, floor:7, type:'landmark', label:'Education'},
    'Assoc_Dean_Sciences': {x:495, y:80, floor:7, type:'landmark', label:'Dean Science'},
    'Lift_7NE': {x:535, y:80, floor:7, type:'lift', label:'Lift NE'},
    'Steps_7NE': {x:450, y:120, floor:7, type:'steps', label:'Stairs NE'},
    '741': {x:380, y:45, floor:7, type:'room', label:'741'},
    '742': {x:410, y:45, floor:7, type:'room', label:'742'},
    '743': {x:440, y:45, floor:7, type:'room', label:'743'},
    '744': {x:470, y:45, floor:7, type:'room', label:'744'},
    '746': {x:500, y:45, floor:7, type:'room', label:'746'},
    '747': {x:530, y:45, floor:7, type:'room', label:'747'},
    '751': {x:380, y:20, floor:7, type:'room', label:'751'},
    '752': {x:410, y:20, floor:7, type:'room', label:'752'},
    '753': {x:440, y:20, floor:7, type:'room', label:'753'},
    '754': {x:470, y:20, floor:7, type:'room', label:'754'},
    '755': {x:500, y:20, floor:7, type:'room', label:'755'}
  };

  const EDGES = [
    // Floor 5
    ['Steps_5SW', 'Lift_5C'], ['Lift_5C', '501'], ['501', '502'], ['502', '503'], ['503', '504'], ['504', 'Steps_5SE'], ['Steps_5SE', 'Gate_5E'],
    ['Gents_Toilet_5E', 'Ladies_Toilet_5E'], ['Ladies_Toilet_5E', '507A'], ['507A', '507'], ['507', '506'], ['506', '505'], ['505', 'Steps_5SE'],
    ['513', '514'], ['514', '515'], ['515', '516'], ['516', '517'], ['517', '518'], ['518', 'Ladies_Toilet_5W'], ['Ladies_Toilet_5W', 'Gents_Toilet_5W'], ['Gents_Toilet_5W', '521'], ['521', '522'],
    ['Water_5', 'Hall_5'], ['Hall_5', 'Seminar_Hall'], ['Seminar_Hall', '526'], ['526', '527'], ['527', 'Dept_of_Commerce'], ['Dept_of_Commerce', 'Lift_5NE'],
    ['522', 'Water_5'], ['513', 'Steps_5SW'],
    ['526', '523'], ['523', '524'], ['524', 'Steps_5NE'], ['Steps_5NE', 'Gate_5NE'], ['Lift_5NE', 'Steps_5NE'], ['Steps_5NE', 'Gents_Toilet_5E'],
    ['Steps_5SW', 'Xerox_5'], ['Xerox_5', 'Physics_Lab'], ['Physics_Lab', 'Small_Gate_5'],
    ['Seminar_Hall', 'Panel_Room'],

    // Floor 6
    ['Lift_6C', '601'], ['601', 'Quantum_Computing'], ['Quantum_Computing', '602'], ['602', '603'], ['603', 'Steps_6E'],
    ['Gents_Toilet_6E', 'Ladies_Toilet_6E'], ['Ladies_Toilet_6E', '607A'], ['607A', '607'], ['607', '606'], ['606', '605'], ['605', '604'], ['604', 'Steps_6E'],
    ['613', 'Dept_of_Math'], ['Dept_of_Math', '615'], ['615', '616'], ['616', '617'], ['617', 'Energy_Science_Lab'], ['Energy_Science_Lab', 'Ladies_Toilet_6W'], ['Ladies_Toilet_6W', 'Gents_Toilet_6W'], ['Gents_Toilet_6W', '621'], ['621', 'Dept_of_CS_W'],
    ['Water_6', '625'], ['625', '626'], ['626', '627'], ['627', 'Dept_of_CS_N'], ['Dept_of_CS_N', 'Lift_6NE'],
    ['Dept_of_CS_W', 'Water_6'], ['613', 'Lift_6C'],
    ['626', '623'], ['623', '624'], ['624', 'Steps_6NE'], ['Lift_6NE', 'Steps_6NE'], ['Steps_6NE', 'Gents_Toilet_6E'],

    // Floor 7
    ['Lift_7C', '701'], ['701', '702'], ['702', '703'], ['703', '704'], ['704', 'Steps_7E'],
    ['Gents_Toilet_7E', 'Ladies_Toilet_7E'], ['Ladies_Toilet_7E', '709C'], ['709C', '708'], ['708', '707'], ['707', '705'], ['705', 'Steps_7E'],
    ['710', '711'], ['711', '713'], ['713', '714'], ['714', '715'], ['715', '716'], ['716', '717'], ['717', '718'], ['718', 'Ladies_Toilet_7W'], ['Ladies_Toilet_7W', 'Gents_Toilet_7W'], ['Gents_Toilet_7W', '722'],
    ['721', 'Prayer_Hall'], ['Prayer_Hall', 'Assembly_Hall'], ['Assembly_Hall', '725'], ['725', '727'], ['727', 'School_of_Education'], ['School_of_Education', 'Assoc_Dean_Sciences'], ['Assoc_Dean_Sciences', 'Lift_7NE'],
    ['722', '721'], ['710', 'Lift_7C'],
    ['725', '724'], ['724', 'Steps_7NE'], ['Lift_7NE', 'Steps_7NE'], ['Steps_7NE', 'Gents_Toilet_7E'],
    ['Dept_of_Psychology', '715'],
    ['741', '742'], ['742', '743'], ['743', '744'], ['744', '746'], ['746', '747'],
    ['751', '752'], ['752', '753'], ['753', '754'], ['754', '755'],
    ['727', '741'], ['741', '751']
  ];

  class FloorMapRenderer {
    constructor() {
      this.canvas = null;
      this.ctx = null;
      this.currentFloor = 5;
      this.currentNode = null;
      this.destinationNode = null;
      this.route = [];
      this.dashOffset = 0;

      // Pointer animation
      this.animState = {
        active: false,
        startTime: 0,
        startX: 0,
        startY: 0,
        targetX: 0,
        targetY: 0,
        duration: 700,
        pulsePhase: 0
      };

      this.draw = this.draw.bind(this);
    }

    init(canvasId) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) return;
      this.ctx = this.canvas.getContext('2d');

      // Setup High-DPI rendering
      this.resizeCanvas();
      window.addEventListener('resize', () => this.resizeCanvas());

      requestAnimationFrame(this.draw);
    }

    resizeCanvas() {
      if (!this.canvas) return;
      const dpr = window.devicePixelRatio || 1;
      const rect = this.canvas.getBoundingClientRect();
      const logicalWidth = 600;
      const logicalHeight = 520;

      this.canvas.width = logicalWidth * dpr;
      this.canvas.height = logicalHeight * dpr;
      this.ctx.scale(dpr, dpr);
      this.logicalWidth = logicalWidth;
      this.logicalHeight = logicalHeight;
    }

    setFloor(floorNum) {
      this.currentFloor = parseInt(floorNum);
    }

    setCurrentNode(nodeId) {
      const target = NODE_COORDS[nodeId];
      if (!target) return;

      if (target.floor !== this.currentFloor) {
        this.setFloor(target.floor);
      }

      if (this.currentNode && NODE_COORDS[this.currentNode]) {
        const start = NODE_COORDS[this.currentNode];
        this.animState = {
          active: true,
          startTime: performance.now(),
          startX: start.x,
          startY: start.y,
          targetX: target.x,
          targetY: target.y,
          duration: 700,
          pulsePhase: this.animState.pulsePhase
        };
      }
      this.currentNode = nodeId;
    }

    setDestination(nodeId) {
      this.destinationNode = nodeId;
      const target = NODE_COORDS[nodeId];
      if (target && target.floor !== this.currentFloor) {
        this.setFloor(target.floor);
      }
    }

    setRoute(nodeIdArray) {
      this.route = nodeIdArray || [];
    }

    clearRoute() {
      this.route = [];
      this.destinationNode = null;
      this.currentNode = null;
    }

    getFloorForNode(nodeId) {
      return NODE_COORDS[nodeId] ? NODE_COORDS[nodeId].floor : null;
    }

    draw(timestamp) {
      if (!this.ctx) return;
      const w = this.logicalWidth || 600;
      const h = this.logicalHeight || 520;

      // 1. Blueprint Grid Background
      this.drawBackground(w, h);

      // 2. Central Garden Courtyard
      this.drawGarden();

      // 3. Corridor Paths (Network)
      this.drawCorridors();

      // 4. Animated Active Route Path
      this.drawRoute();

      // 5. Facility & Room Nodes
      this.drawNodes();

      // 6. Destination Pin
      this.drawDestinationPin(timestamp);

      // 7. Dynamic User Location Radar Pointer
      this.drawUserPointer(timestamp);

      // 8. Compass & Floor Indicator HUD
      this.drawHUD();

      // Continue animation loop
      requestAnimationFrame(this.draw);
    }

    drawBackground(w, h) {
      // Dark gradient fill
      const grad = this.ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, '#090d16');
      grad.addColorStop(1, '#0e1422');
      this.ctx.fillStyle = grad;
      this.ctx.fillRect(0, 0, w, h);

      // Subtle architectural grid
      this.ctx.strokeStyle = 'rgba(30, 41, 59, 0.45)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      for (let x = 20; x < w; x += 30) {
        this.ctx.moveTo(x, 0);
        this.ctx.lineTo(x, h);
      }
      for (let y = 20; y < h; y += 30) {
        this.ctx.moveTo(0, y);
        this.ctx.lineTo(w, y);
      }
      this.ctx.stroke();
    }

    drawGarden() {
      const rx = 145, ry = 145, rw = 330, rh = 265, radius = 24;

      // Outer grass glow
      this.ctx.shadowColor = 'rgba(16, 185, 129, 0.2)';
      this.ctx.shadowBlur = 18;

      // Lush Garden Gradient
      const gardenGrad = this.ctx.createLinearGradient(rx, ry, rx + rw, ry + rh);
      gardenGrad.addColorStop(0, '#0d3822');
      gardenGrad.addColorStop(1, '#082818');
      this.ctx.fillStyle = gardenGrad;

      this.ctx.beginPath();
      this.ctx.roundRect ? this.ctx.roundRect(rx, ry, rw, rh, radius) : this.ctx.rect(rx, ry, rw, rh);
      this.ctx.fill();

      // Soft Garden Border
      this.ctx.shadowBlur = 0;
      this.ctx.strokeStyle = 'rgba(52, 211, 153, 0.35)';
      this.ctx.lineWidth = 2;
      this.ctx.stroke();

      // Inner courtyard lawn stripes / texture
      this.ctx.strokeStyle = 'rgba(16, 185, 129, 0.08)';
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      for (let i = rx + 20; i < rx + rw; i += 28) {
        this.ctx.moveTo(i, ry + 15);
        this.ctx.lineTo(i + 15, ry + rh - 15);
      }
      this.ctx.stroke();

      // Foliage decor dots (Trees)
      const trees = [
        {x: rx + 40, y: ry + 40}, {x: rx + rw - 40, y: ry + 40},
        {x: rx + 40, y: ry + rh - 40}, {x: rx + rw - 40, y: ry + rh - 40},
        {x: rx + rw / 2 - 60, y: ry + rh / 2}, {x: rx + rw / 2 + 60, y: ry + rh / 2}
      ];
      trees.forEach(t => {
        this.ctx.fillStyle = 'rgba(34, 197, 94, 0.35)';
        this.ctx.beginPath();
        this.ctx.arc(t.x, t.y, 8, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = '#4ade80';
        this.ctx.beginPath();
        this.ctx.arc(t.x, t.y, 3, 0, Math.PI * 2);
        this.ctx.fill();
      });

      // Centered Courtyard Label
      this.ctx.fillStyle = '#6ee7b7';
      this.ctx.font = 'bold 15px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText("🌿 CENTRAL COURTYARD GARDEN", rx + rw / 2, ry + rh / 2 - 10);

      this.ctx.fillStyle = 'rgba(110, 231, 183, 0.6)';
      this.ctx.font = '11px Inter, sans-serif';
      this.ctx.fillText("(Non-walkable zone)", rx + rw / 2, ry + rh / 2 + 10);
    }

    drawCorridors() {
      // 1. Broad corridor track glow
      this.ctx.strokeStyle = '#1e293b';
      this.ctx.lineWidth = 14;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      this.ctx.beginPath();
      EDGES.forEach(edge => {
        const n1 = NODE_COORDS[edge[0]];
        const n2 = NODE_COORDS[edge[1]];
        if (n1 && n2 && n1.floor === this.currentFloor && n2.floor === this.currentFloor) {
          this.ctx.moveTo(n1.x, n1.y);
          this.ctx.lineTo(n2.x, n2.y);
        }
      });
      this.ctx.stroke();

      // 2. Inner walkway line
      this.ctx.strokeStyle = '#334155';
      this.ctx.lineWidth = 4;
      this.ctx.beginPath();
      EDGES.forEach(edge => {
        const n1 = NODE_COORDS[edge[0]];
        const n2 = NODE_COORDS[edge[1]];
        if (n1 && n2 && n1.floor === this.currentFloor && n2.floor === this.currentFloor) {
          this.ctx.moveTo(n1.x, n1.y);
          this.ctx.lineTo(n2.x, n2.y);
        }
      });
      this.ctx.stroke();
    }

    drawRoute() {
      if (!this.route || this.route.length < 2) return;

      // Extract points on current floor
      const points = [];
      for (let id of this.route) {
        const n = NODE_COORDS[id];
        if (n && n.floor === this.currentFloor) {
          points.push(n);
        }
      }
      if (points.length < 2) return;

      // Animate marching dash
      this.dashOffset -= 0.8;

      // 1. Outer Neon Route Glow
      this.ctx.shadowColor = 'rgba(56, 189, 248, 0.8)';
      this.ctx.shadowBlur = 12;
      this.ctx.strokeStyle = '#38bdf8';
      this.ctx.lineWidth = 5;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';
      this.ctx.setLineDash([10, 6]);
      this.ctx.lineDashOffset = this.dashOffset;

      this.ctx.beginPath();
      this.ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        this.ctx.lineTo(points[i].x, points[i].y);
      }
      this.ctx.stroke();

      // 2. Core bright center line
      this.ctx.shadowBlur = 0;
      this.ctx.strokeStyle = '#ffffff';
      this.ctx.lineWidth = 2;
      this.ctx.setLineDash([4, 12]);
      this.ctx.lineDashOffset = this.dashOffset * 1.5;
      this.ctx.stroke();

      this.ctx.setLineDash([]); // Reset dash
    }

    drawNodes() {
      const isRouteNode = (id) => this.route.includes(id);

      Object.entries(NODE_COORDS).forEach(([id, node]) => {
        if (node.floor !== this.currentFloor) return;

        const onRoute = isRouteNode(id);
        const radius = onRoute ? 7 : 5;

        let fillColor = '#475569';
        let strokeColor = '#64748b';
        let badgeIcon = null;

        if (node.type === 'lift') {
          fillColor = '#2563eb';
          strokeColor = '#60a5fa';
          badgeIcon = '🛗';
        } else if (node.type === 'steps') {
          fillColor = '#7c3aed';
          strokeColor = '#a78bfa';
          badgeIcon = '🪜';
        } else if (node.type === 'toilet') {
          fillColor = '#334155';
          strokeColor = '#475569';
        } else if (node.type === 'gate') {
          fillColor = '#d97706';
          strokeColor = '#fbbf24';
        } else if (node.type === 'landmark') {
          fillColor = '#0d9488';
          strokeColor = '#2dd4bf';
        }

        if (onRoute) {
          fillColor = '#38bdf8';
          strokeColor = '#ffffff';
        }

        // Draw node circle
        this.ctx.shadowColor = onRoute ? 'rgba(56, 189, 248, 0.6)' : 'transparent';
        this.ctx.shadowBlur = onRoute ? 8 : 0;
        this.ctx.fillStyle = fillColor;
        this.ctx.strokeStyle = strokeColor;
        this.ctx.lineWidth = 1.5;

        this.ctx.beginPath();
        this.ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Draw node labels
        if (node.type === 'room' || node.type === 'landmark' || onRoute) {
          const text = node.label || id.replace(/_/g, ' ');
          this.ctx.font = onRoute ? 'bold 11px Inter, sans-serif' : '10px Inter, sans-serif';
          
          const textMetrics = this.ctx.measureText(text);
          const tx = node.x > 300 ? node.x - textMetrics.width - 12 : node.x + 12;
          const ty = node.y;

          // Label Pill Background
          this.ctx.fillStyle = onRoute ? 'rgba(15, 23, 42, 0.9)' : 'rgba(15, 23, 42, 0.65)';
          this.ctx.fillRect(tx - 3, ty - 7, textMetrics.width + 6, 14);

          this.ctx.fillStyle = onRoute ? '#38bdf8' : (node.type === 'landmark' ? '#5eead4' : '#cbd5e1');
          this.ctx.textAlign = 'left';
          this.ctx.textBaseline = 'middle';
          this.ctx.fillText(text, tx, ty);
        } else if (badgeIcon) {
          // Facility Icon
          this.ctx.font = '10px sans-serif';
          this.ctx.textAlign = 'center';
          this.ctx.textBaseline = 'bottom';
          this.ctx.fillText(badgeIcon, node.x, node.y - 6);
        }
      });
    }

    drawDestinationPin(timestamp) {
      if (!this.destinationNode) return;
      const dest = NODE_COORDS[this.destinationNode];
      if (!dest || dest.floor !== this.currentFloor) return;

      // Floating bounce animation
      const bounce = Math.sin(timestamp * 0.005) * 4;
      const px = dest.x;
      const py = dest.y - 12 + bounce;

      // Ground ripple target
      const ripple = (timestamp * 0.003) % 1;
      this.ctx.strokeStyle = `rgba(239, 68, 68, ${1 - ripple})`;
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.ellipse(dest.x, dest.y, 14 * ripple + 4, 7 * ripple + 2, 0, 0, Math.PI * 2);
      this.ctx.stroke();

      // Pin Body Glow
      this.ctx.shadowColor = '#ef4444';
      this.ctx.shadowBlur = 14;

      // Pin Diamond
      this.ctx.fillStyle = '#ef4444';
      this.ctx.beginPath();
      this.ctx.moveTo(px, py - 10);
      this.ctx.lineTo(px + 8, py);
      this.ctx.lineTo(px, py + 10);
      this.ctx.lineTo(px - 8, py);
      this.ctx.closePath();
      this.ctx.fill();

      // Center Pin Dot
      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(px, py, 3, 0, Math.PI * 2);
      this.ctx.fill();

      this.ctx.shadowBlur = 0;

      // Floating Badge
      const labelText = `🎯 ${dest.label || this.destinationNode}`;
      this.ctx.font = 'bold 12px Inter, sans-serif';
      const tw = this.ctx.measureText(labelText).width;

      this.ctx.fillStyle = '#ef4444';
      this.ctx.beginPath();
      this.ctx.roundRect ? this.ctx.roundRect(px - tw/2 - 6, py - 26, tw + 12, 18, 9) : this.ctx.rect(px - tw/2 - 6, py - 26, tw + 12, 18);
      this.ctx.fill();

      this.ctx.fillStyle = '#ffffff';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(labelText, px, py - 17);
    }

    drawUserPointer(timestamp) {
      if (!this.currentNode) return;
      const target = NODE_COORDS[this.currentNode];
      if (!target || target.floor !== this.currentFloor) return;

      let x = target.x;
      let y = target.y;

      // Smooth interpolation
      if (this.animState.active) {
        const elapsed = timestamp - this.animState.startTime;
        const progress = Math.min(elapsed / this.animState.duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3); // easeOutCubic

        x = this.animState.startX + (this.animState.targetX - this.animState.startX) * ease;
        y = this.animState.startY + (this.animState.targetY - this.animState.startY) * ease;

        if (progress >= 1) {
          this.animState.active = false;
        }
      }

      // Radar Concentric Pulses
      this.animState.pulsePhase += 0.04;
      const pulse1 = (Math.sin(this.animState.pulsePhase) + 1) / 2;
      const pulse2 = (Math.sin(this.animState.pulsePhase + Math.PI / 2) + 1) / 2;

      // Outer radar waves
      this.ctx.strokeStyle = `rgba(56, 189, 248, ${(1 - pulse1) * 0.7})`;
      this.ctx.lineWidth = 2;
      this.ctx.beginPath();
      this.ctx.arc(x, y, 10 + pulse1 * 22, 0, Math.PI * 2);
      this.ctx.stroke();

      this.ctx.strokeStyle = `rgba(56, 189, 248, ${(1 - pulse2) * 0.4})`;
      this.ctx.beginPath();
      this.ctx.arc(x, y, 6 + pulse2 * 16, 0, Math.PI * 2);
      this.ctx.stroke();

      // Glowing Center Core
      this.ctx.shadowColor = '#38bdf8';
      this.ctx.shadowBlur = 16;
      this.ctx.fillStyle = '#38bdf8';
      this.ctx.beginPath();
      this.ctx.arc(x, y, 7, 0, Math.PI * 2);
      this.ctx.fill();

      this.ctx.fillStyle = '#ffffff';
      this.ctx.beginPath();
      this.ctx.arc(x, y, 3, 0, Math.PI * 2);
      this.ctx.fill();
      this.ctx.shadowBlur = 0;

      // "YOU" Floating Badge
      const youBadge = "📍 YOU ARE HERE";
      this.ctx.font = 'bold 11px Inter, sans-serif';
      const bw = this.ctx.measureText(youBadge).width;

      this.ctx.fillStyle = '#38bdf8';
      this.ctx.beginPath();
      this.ctx.roundRect ? this.ctx.roundRect(x - bw/2 - 6, y - 28, bw + 12, 17, 8) : this.ctx.rect(x - bw/2 - 6, y - 28, bw + 12, 17);
      this.ctx.fill();

      this.ctx.fillStyle = '#0a0f1a';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(youBadge, x, y - 19);
    }

    drawHUD() {
      // Floor watermark
      const floorNames = {5: 'GROUND FLOOR', 6: 'FIRST FLOOR', 7: 'SECOND FLOOR'};
      this.ctx.fillStyle = 'rgba(148, 163, 184, 0.15)';
      this.ctx.font = '900 24px Inter, sans-serif';
      this.ctx.textAlign = 'right';
      this.ctx.textBaseline = 'top';
      this.ctx.fillText(floorNames[this.currentFloor] || '', this.logicalWidth - 20, 16);

      // Mini Compass
      const cx = 35, cy = 35;
      this.ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, 14, 0, Math.PI * 2);
      this.ctx.stroke();

      this.ctx.fillStyle = '#ef4444';
      this.ctx.font = 'bold 10px Inter, sans-serif';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText('N', cx, cy - 6);

      this.ctx.fillStyle = 'rgba(148, 163, 184, 0.8)';
      this.ctx.fillText('S', cx, cy + 6);
    }
  }

  const mapInstance = new FloorMapRenderer();

  window.FloorMap = {
    init: (canvasId) => mapInstance.init(canvasId),
    setFloor: (floorNum) => mapInstance.setFloor(floorNum),
    setCurrentNode: (nodeId) => mapInstance.setCurrentNode(nodeId),
    setDestination: (nodeId) => mapInstance.setDestination(nodeId),
    setRoute: (nodeIdArray) => mapInstance.setRoute(nodeIdArray),
    clearRoute: () => mapInstance.clearRoute(),
    getFloorForNode: (nodeId) => mapInstance.getFloorForNode(nodeId)
  };

})();
