/**
 * App.jsx — IPL Crowd Management Bento Dashboard
 *
 * Assembles all components into a responsive bento grid layout.
 * Uses simulated data for the prototype; production wires to
 * Firestore listeners via useFirestore hooks.
 */

import { useState, useEffect, useCallback } from 'react';
import './App.css';

// Components
import Navbar from './components/Navbar';
import BentoGrid, { BentoItem } from './components/BentoGrid';
import DensityGauge from './components/DensityGauge';
import GateCard from './components/GateCard';
import StadiumMap from './components/StadiumMap';
import StrictProtocolHub from './components/StrictProtocolHub';
import MatchDayPanel from './components/MatchDayPanel';
import CrowdsourcedFeed from './components/CrowdsourcedFeed';
import EvacuNetAlert from './components/EvacuNetAlert';

// Data
import { GATES } from './utils/constants';

// ── Simulated real-time data for the prototype ───────────────
function generateGateMetrics() {
  const metrics = {};
  GATES.forEach((gate) => {
    const density = 0.2 + Math.random() * 2.5;
    metrics[gate.id] = {
      density,
      wait_time: Math.round(2 + Math.random() * 18),
      throughput: Math.round(30 + Math.random() * 90),
      strict_protocol: density > 2.0,
    };
  });
  return metrics;
}

function generateSensorData() {
  return {
    temperature: 28 + Math.random() * 10,
    humidity: 55 + Math.random() * 30,
    co2: 350 + Math.random() * 400,
    pm25: 15 + Math.random() * 50,
    tvoc: 80 + Math.random() * 300,
    noise_level: 60 + Math.random() * 30,
  };
}

function App() {
  const [gateMetrics, setGateMetrics] = useState(generateGateMetrics);
  const [sensorData, setSensorData] = useState(generateSensorData);
  const [evacunetScore, setEvacunetScore] = useState(0.12);
  const [evacuationActive, setEvacuationActive] = useState(false);
  const connectionStatus = 'connected';

  // Compute aggregate density (average across all gates)
  const avgDensity =
    Object.values(gateMetrics).reduce((sum, m) => sum + m.density, 0) /
    Object.keys(gateMetrics).length;

  // Determine if strict protocol is active anywhere
  const strictProtocolGates = Object.entries(gateMetrics)
    .filter(([, m]) => m.strict_protocol)
    .map(([id]) => id);

  // Simulate real-time data refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setGateMetrics(generateGateMetrics());
      setSensorData(generateSensorData());
      setEvacunetScore(Math.random() * 0.3 + 0.05);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleEvacuationAcknowledge = useCallback(() => {
    setEvacuationActive(false);
  }, []);

  return (
    <div className="app-shell" id="app-root">
      <Navbar connectionStatus={connectionStatus} />

      <main className="dashboard-main">
        <BentoGrid>
          {/* ── Row 1: Stadium Map + Density Gauge ─────────── */}
          <BentoItem span="wide" id="panel-map" className="bento-item-tall">
            <StadiumMap gateMetrics={gateMetrics} />
          </BentoItem>

          <BentoItem span="normal" id="panel-density">
            <DensityGauge density={avgDensity} label="Overall Density" />
          </BentoItem>

          <BentoItem span="normal" id="panel-protocol">
            <StrictProtocolHub
              active={strictProtocolGates.length > 0}
              activatedGates={strictProtocolGates}
            />
          </BentoItem>

          {/* ── Row 2: Match Day Panel + Feed ──────────────── */}
          <BentoItem span="wide" id="panel-matchday">
            <MatchDayPanel
              sensorData={sensorData}
              evacunetScore={evacunetScore}
            />
          </BentoItem>

          <BentoItem span="wide" id="panel-feed" className="bento-item-tall">
            <CrowdsourcedFeed />
          </BentoItem>

          {/* ── Row 3: Gate Cards ──────────────────────────── */}
          {GATES.map((gate) => (
            <BentoItem key={gate.id} id={`panel-${gate.id}`}>
              <GateCard gate={gate} metrics={gateMetrics[gate.id] || {}} />
            </BentoItem>
          ))}
        </BentoGrid>
      </main>

      {/* Full-screen evacuation overlay (hidden unless triggered) */}
      <EvacuNetAlert
        active={evacuationActive}
        hazardScore={evacunetScore}
        affectedZones={['North Stand', 'East Gallery']}
        reason="EvacuNet hazard probability exceeded 85% threshold"
        onAcknowledge={handleEvacuationAcknowledge}
      />
    </div>
  );
}

export default App;
