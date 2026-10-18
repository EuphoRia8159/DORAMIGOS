/**
 * AEGIS Geospatial Radar & Fleet Canvas Map
 * Renders high-fidelity radar grid, hospital nodes, moving ambulances,
 * emergency distress beacons, and active dispatch vectors.
 */

class AEGISRadarMap {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        // Bounds for coordinate projection (Metro region)
        this.minLat = 40.7000;
        this.maxLat = 40.7800;
        this.minLon = -74.0250;
        this.maxLon = -73.9500;

        // Data caches
        this.hospitals = [];
        this.ambulances = [];
        this.emergencies = [];
        this.hoveredObject = null;

        // Animation state
        this.radarAngle = 0;
        this.pulsePhase = 0;
        this.dashOffset = 0;

        this.initCanvas();
        this.bindEvents();
        this.startLoop();
    }

    initCanvas() {
        const resize = () => {
            const rect = this.canvas.getBoundingClientRect();
            this.canvas.width = rect.width * window.devicePixelRatio;
            this.canvas.height = rect.height * window.devicePixelRatio;
            this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            this.displayWidth = rect.width;
            this.displayHeight = rect.height;
        };
        resize();
        window.addEventListener('resize', resize);
    }

    bindEvents() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            this.checkHover(mouseX, mouseY);
        });

        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredObject = null;
        });
    }

    project(lat, lon) {
        const padding = 40;
        const w = this.displayWidth - (padding * 2);
        const h = this.displayHeight - (padding * 2);

        const x = padding + ((lon - this.minLon) / (this.maxLon - this.minLon)) * w;
        // Invert Y because latitude goes north (up) while screen Y goes down
        const y = padding + ((this.maxLat - lat) / (this.maxLat - this.minLat)) * h;
        return { x, y };
    }

    updateData(hospitals, ambulances, emergencies) {
        if (hospitals) this.hospitals = hospitals;
        if (ambulances) this.ambulances = ambulances;
        if (emergencies) this.emergencies = emergencies;
    }

    startLoop() {
        const render = () => {
            this.draw();
            this.radarAngle = (this.radarAngle + 0.015) % (Math.PI * 2);
            this.pulsePhase = (this.pulsePhase + 0.04) % (Math.PI * 2);
            this.dashOffset = (this.dashOffset - 0.5) % 16;
            requestAnimationFrame(render);
        };
        requestAnimationFrame(render);
    }

    draw() {
        const ctx = this.ctx;
        const w = this.displayWidth;
        const h = this.displayHeight;

        // 1. Clear & Dark Background
        ctx.fillStyle = '#080d1a';
        ctx.fillRect(0, 0, w, h);

        // 2. Draw Subtle Radar Grid & Concentric Rings
        const cx = w / 2;
        const cy = h / 2;
        const maxRadius = Math.min(w, h) * 0.48;

        ctx.save();
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.08)';
        ctx.lineWidth = 1;

        // Concentric circles
        for (let r = maxRadius * 0.25; r <= maxRadius; r += maxRadius * 0.25) {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.stroke();
        }

        // Crosshairs
        ctx.beginPath();
        ctx.moveTo(cx - maxRadius, cy);
        ctx.lineTo(cx + maxRadius, cy);
        ctx.moveTo(cx, cy - maxRadius);
        ctx.lineTo(cx, cy + maxRadius);
        ctx.stroke();

        // 3. Radar Sweep Beam
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxRadius);
        grad.addColorStop(0, 'rgba(56, 189, 248, 0.15)');
        grad.addColorStop(1, 'rgba(56, 189, 248, 0)');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, maxRadius, this.radarAngle - 0.35, this.radarAngle);
        ctx.closePath();
        ctx.fill();

        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(this.radarAngle) * maxRadius, cy + Math.sin(this.radarAngle) * maxRadius);
        ctx.stroke();
        ctx.restore();

        // 4. Draw Active Dispatch Trajectory Vectors
        this.ambulances.forEach(amb => {
            if (amb.status.includes('DISPATCHED') || amb.status.includes('EN_ROUTE')) {
                const ambPos = this.project(amb.latitude, amb.longitude);
                if (amb.target_latitude && amb.target_longitude) {
                    const targetPos = this.project(amb.target_latitude, amb.target_longitude);

                    ctx.save();
                    ctx.strokeStyle = '#38bdf8';
                    ctx.lineWidth = 2;
                    ctx.setLineDash([6, 6]);
                    ctx.lineDashOffset = this.dashOffset;
                    ctx.beginPath();
                    ctx.moveTo(ambPos.x, ambPos.y);
                    ctx.lineTo(targetPos.x, targetPos.y);
                    ctx.stroke();
                    ctx.restore();
                }
            }
        });

        // 5. Draw Hospitals
        this.hospitals.forEach(hosp => {
            const pos = this.project(hosp.latitude, hosp.longitude);
            const isHovered = this.hoveredObject && this.hoveredObject.type === 'hospital' && this.hoveredObject.data.id === hosp.id;

            ctx.save();
            // Outer glow
            const glowColor = hosp.trauma_level === 'Level 1' ? 'rgba(244, 63, 94, 0.4)' : 'rgba(56, 189, 248, 0.4)';
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = isHovered ? 15 : 8;

            // Pin marker
            ctx.fillStyle = hosp.trauma_level === 'Level 1' ? '#f43f5e' : (hosp.trauma_level === 'Level 2' ? '#38bdf8' : '#10b981');
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, isHovered ? 8 : 6, 0, Math.PI * 2);
            ctx.fill();

            // Inner cross
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(pos.x - 1, pos.y - 3, 2, 6);
            ctx.fillRect(pos.x - 3, pos.y - 1, 6, 2);

            // Label
            ctx.shadowBlur = 0;
            ctx.font = '600 9px "Plus Jakarta Sans", sans-serif';
            ctx.fillStyle = '#cbd5e1';
            ctx.textAlign = 'center';
            ctx.fillText(hosp.code, pos.x, pos.y + 14);

            // IBM Z indicator dot
            if (hosp.ibm_z_connected) {
                ctx.fillStyle = '#60a5fa';
                ctx.beginPath();
                ctx.arc(pos.x + 8, pos.y - 6, 3, 0, Math.PI * 2);
                ctx.fill();
            }

            ctx.restore();
        });

        // 6. Draw Emergencies
        this.emergencies.forEach(emrg => {
            if (emrg.status === 'RESOLVED' || emrg.status === 'CANCELLED') return;
            const pos = this.project(emrg.latitude, emrg.longitude);

            ctx.save();
            // Pulse wave
            const pulseR = 8 + (Math.sin(this.pulsePhase) + 1) * 6;
            ctx.strokeStyle = emrg.severity === 'CRITICAL' ? 'rgba(244, 63, 94, 0.6)' : 'rgba(251, 146, 60, 0.6)';
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, pulseR, 0, Math.PI * 2);
            ctx.stroke();

            // Distress beacon dot
            ctx.fillStyle = emrg.severity === 'CRITICAL' ? '#f43f5e' : '#fb923c';
            ctx.shadowColor = ctx.fillStyle;
            ctx.shadowBlur = 12;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 6, 0, Math.PI * 2);
            ctx.fill();

            ctx.shadowBlur = 0;
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 8px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('!', pos.x, pos.y + 3);

            ctx.restore();
        });

        // 7. Draw Ambulances
        this.ambulances.forEach(amb => {
            const pos = this.project(amb.latitude, amb.longitude);
            const isHovered = this.hoveredObject && this.hoveredObject.type === 'ambulance' && this.hoveredObject.data.id === amb.id;

            ctx.save();
            const isBusy = amb.status !== 'AVAILABLE';
            const ambColor = isBusy ? '#fbbf24' : '#34d399';

            ctx.shadowColor = ambColor;
            ctx.shadowBlur = isHovered ? 12 : 6;
            ctx.fillStyle = ambColor;

            if (amb.vehicle_type === 'AIR') {
                // Diamond marker for helicopter
                ctx.beginPath();
                ctx.moveTo(pos.x, pos.y - 7);
                ctx.lineTo(pos.x + 7, pos.y);
                ctx.lineTo(pos.x, pos.y + 7);
                ctx.lineTo(pos.x - 7, pos.y);
                ctx.closePath();
                ctx.fill();
            } else {
                // Square/circle marker for ground unit
                ctx.beginPath();
                ctx.arc(pos.x, pos.y, isHovered ? 6 : 4.5, 0, Math.PI * 2);
                ctx.fill();
            }

            ctx.shadowBlur = 0;
            ctx.font = '600 8px "JetBrains Mono", monospace';
            ctx.fillStyle = '#94a3b8';
            ctx.textAlign = 'center';
            ctx.fillText(amb.call_sign.split('-')[1] || amb.call_sign, pos.x, pos.y - 8);

            ctx.restore();
        });

        // 8. Draw Hover Tooltip if item hovered
        if (this.hoveredObject) {
            this.drawTooltip(this.hoveredObject);
        }
    }

    checkHover(mouseX, mouseY) {
        const threshold = 12;
        this.hoveredObject = null;

        // Check emergencies
        for (const emrg of this.emergencies) {
            const pos = this.project(emrg.latitude, emrg.longitude);
            if (Math.hypot(pos.x - mouseX, pos.y - mouseY) < threshold) {
                this.hoveredObject = { type: 'emergency', data: emrg, pos };
                return;
            }
        }

        // Check ambulances
        for (const amb of this.ambulances) {
            const pos = this.project(amb.latitude, amb.longitude);
            if (Math.hypot(pos.x - mouseX, pos.y - mouseY) < threshold) {
                this.hoveredObject = { type: 'ambulance', data: amb, pos };
                return;
            }
        }

        // Check hospitals
        for (const hosp of this.hospitals) {
            const pos = this.project(hosp.latitude, hosp.longitude);
            if (Math.hypot(pos.x - mouseX, pos.y - mouseY) < threshold) {
                this.hoveredObject = { type: 'hospital', data: hosp, pos };
                return;
            }
        }
    }

    drawTooltip(item) {
        const ctx = this.ctx;
        let title = '';
        let line1 = '';
        let line2 = '';

        if (item.type === 'hospital') {
            title = item.data.name;
            line1 = `${item.data.trauma_level} • Beds: ${item.data.available_beds}/${item.data.total_beds} (ICU: ${item.data.icu_available})`;
            line2 = `ER Load: ${item.data.er_current_load}/${item.data.er_capacity} (${Math.round(item.data.er_occupancy_rate * 100)}%) ${item.data.ibm_z_connected ? '• IBM Z Verified' : ''}`;
        } else if (item.type === 'ambulance') {
            title = `${item.data.call_sign} (${item.data.vehicle_type})`;
            line1 = `Status: ${item.data.status} • Crew: ${item.data.paramedic_crew}`;
            line2 = `Speed: ${item.data.speed_kmh} km/h • Equip: ${item.data.equipment_level}`;
        } else if (item.type === 'emergency') {
            title = `${item.data.emergency_code} [${item.data.severity}]`;
            line1 = `${item.data.category.replace('_', ' ')}: ${item.data.location_name}`;
            line2 = item.data.chief_complaint.slice(0, 45) + '...';
        }

        ctx.save();
        ctx.font = '700 10px "Plus Jakarta Sans", sans-serif';
        const titleW = ctx.measureText(title).width;
        ctx.font = '9px "Plus Jakarta Sans", sans-serif';
        const l1W = ctx.measureText(line1).width;
        const boxW = Math.max(titleW, l1W) + 20;
        const boxH = 46;

        let tx = item.pos.x + 10;
        let ty = item.pos.y - boxH - 5;
        if (tx + boxW > this.displayWidth) tx = item.pos.x - boxW - 10;
        if (ty < 5) ty = item.pos.y + 15;

        ctx.fillStyle = 'rgba(7, 9, 14, 0.92)';
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.4)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.roundRect(tx, ty, boxW, boxH, 6);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = '#38bdf8';
        ctx.font = '700 10px "Plus Jakarta Sans", sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(title, tx + 8, ty + 15);

        ctx.fillStyle = '#e2e8f0';
        ctx.font = '9px "Plus Jakarta Sans", sans-serif';
        ctx.fillText(line1, tx + 8, ty + 28);

        ctx.fillStyle = '#94a3b8';
        ctx.font = '8px "Plus Jakarta Sans", sans-serif';
        ctx.fillText(line2, tx + 8, ty + 40);

        ctx.restore();
    }
}

window.AEGISRadarMap = AEGISRadarMap;
