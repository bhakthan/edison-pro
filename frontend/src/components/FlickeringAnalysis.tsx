import { useState } from 'react';
import { Loader2, Upload, Zap, TrendingUp } from 'lucide-react';
import { api } from '../api/client';
import './FlickeringAnalysis.css';

interface FlickeringAnalysisProps {
  // Empty for now
}

interface AttentionState {
  cycle: number;
  alpha: number;
  source: 'reality' | 'memory';
  mismatch?: number;
}

interface MismatchEvent {
  cycle: number;
  mismatch_score: number;
  novelty_level: string;
  timestamp: string;
}

interface FlickeringResults {
  interpretation: {
    status: string;
    confidence: number;
    explanation: string;
    num_mismatches: number;
    avg_mismatch: number;
  };
  mismatch_events: MismatchEvent[];
  alternatives: any[];
  attention_trace?: AttentionState[];
  system_info: {
    theta_frequency: number;
    mismatch_threshold: number;
    memory_patterns: number;
    cache_size: number;
    total_latency_ms: number;
  };
  num_cycles: number;
  num_mismatches: number;
}

export function FlickeringAnalysis(_props: FlickeringAnalysisProps) {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>('');
  const [numCycles, setNumCycles] = useState(100);
  const [thetaFrequency, setThetaFrequency] = useState(8.0);
  const [domain, setDomain] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<FlickeringResults | null>(null);
  const [error, setError] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAnalyze = async () => {
    if (!imageFile) {
      setError('Please select a diagram image');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    setResults(null);

    try {
      // Convert image to base64
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64 = reader.result as string;

        try {
          const response = await api.analyzeFlickering({
            diagram: base64,
            num_cycles: numCycles,
            theta_frequency: thetaFrequency,
            domain: domain || undefined,
            return_trace: true,
            generate_alternatives: true,
          });

          setResults(response);
        } catch (err) {
          console.error('Analysis error:', err);
          setError(err instanceof Error ? err.message : 'Analysis failed');
        } finally {
          setIsAnalyzing(false);
        }
      };
      reader.readAsDataURL(imageFile);
    } catch (err) {
      console.error('File reading error:', err);
      setError('Failed to read image file');
      setIsAnalyzing(false);
    }
  };

  const renderAttentionTrace = () => {
    if (!results?.attention_trace) return null;

    const trace = results.attention_trace;
    const maxCycles = 100; // Show up to 100 cycles
    const displayTrace = trace.slice(0, maxCycles);

    return (
      <div className="attention-trace">
        <h3>🎯 Attention Trace (Flickering Pattern)</h3>
        <div className="trace-legend">
          <span className="legend-reality">█ Reality</span>
          <span className="legend-memory">█ Memory</span>
        </div>
        <div className="trace-visualization">
          {displayTrace.map((state, idx) => (
            <div key={idx} className="trace-bar-container">
              <div
                className={`trace-bar ${state.source}`}
                style={{
                  height: `${Math.abs(state.alpha * 100)}%`,
                  opacity: state.mismatch && state.mismatch > 0.3 ? 1 : 0.7,
                }}
                title={`Cycle ${state.cycle}: ${state.source} (α=${state.alpha.toFixed(
                  2
                )}${state.mismatch ? `, Δ=${state.mismatch.toFixed(3)}` : ''})`}
              >
                {state.mismatch && state.mismatch > 0.3 && (
                  <span className="mismatch-marker">!</span>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="trace-axis">
          <span>Cycle 0</span>
          <span>Cycle {displayTrace.length}</span>
        </div>
      </div>
    );
  };

  const renderMismatchEvents = () => {
    if (!results?.mismatch_events || results.mismatch_events.length === 0)
      return null;

    return (
      <div className="mismatch-events">
        <h3>⚡ Novelty Detection Events</h3>
        <div className="events-list">
          {results.mismatch_events.map((event, idx) => (
            <div
              key={idx}
              className={`event-card novelty-${event.novelty_level}`}
            >
              <div className="event-header">
                <span className="event-cycle">Cycle {event.cycle}</span>
                <span className="event-novelty">{event.novelty_level}</span>
              </div>
              <div className="event-score">
                Mismatch: {event.mismatch_score.toFixed(3)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flickering-analysis">
      <div className="flickering-header">
        <h2>🌊 Flickering Cognitive Analysis</h2>
        <p>
          Advanced multi-agent analysis inspired by hippocampal navigation.
          The system "flickers" between current perception and historical patterns
          to detect novelty and learn continuously.
        </p>
      </div>

      <div className="flickering-controls">
        <div className="upload-section">
          <label className="upload-label">
            <Upload size={24} />
            <span>{imageFile ? imageFile.name : 'Select Diagram Image'}</span>
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              style={{ display: 'none' }}
            />
          </label>
          {imagePreview && (
            <div className="image-preview">
              <img src={imagePreview} alt="Preview" />
            </div>
          )}
        </div>

        <div className="parameters-section">
          <h3>⚙️ Analysis Parameters</h3>
          <div className="parameter-help-box">
            <p><strong>💡 How Flickering Analysis Works:</strong></p>
            <p>The system rapidly alternates between analyzing the <strong>current diagram</strong> (Reality) and <strong>stored patterns</strong> (Memory) to detect novelty and learn.</p>
            <ul>
              <li><strong>Cycles:</strong> Each cycle compares Reality vs Memory. More cycles = deeper novelty detection. Mismatch scores &gt; 0.5 trigger learning.</li>
              <li><strong>Theta Frequency:</strong> How fast it oscillates (like brain waves). 8 Hz mimics human spatial navigation. Higher = faster but less stable.</li>
              <li><strong>Learning Trigger:</strong> High novelty (&gt;0.5 mismatch) saves new patterns. Low novelty (&lt;0.5) = diagram matches existing knowledge.</li>
            </ul>
          </div>
          <div className="parameter-grid">
            <div className="parameter-control">
              <label>
                🔄 Number of Cycles:
                <input
                  type="number"
                  value={numCycles}
                  onChange={(e) => setNumCycles(parseInt(e.target.value))}
                  min={10}
                  max={200}
                  step={10}
                />
              </label>
              <span className="parameter-hint">
                <strong>50-100 cycles</strong> for normal analysis | <strong>100-200</strong> for complex diagrams
              </span>
            </div>

            <div className="parameter-control">
              <label>
                🌊 Theta Frequency (Hz):
                <input
                  type="number"
                  value={thetaFrequency}
                  onChange={(e) => setThetaFrequency(parseFloat(e.target.value))}
                  min={4}
                  max={10}
                  step={0.5}
                />
              </label>
              <span className="parameter-hint">
                <strong>8 Hz (default)</strong> = optimal brain-like oscillation | <strong>4-6 Hz</strong> = slower/stable | <strong>9-10 Hz</strong> = faster exploration
              </span>
            </div>

            <div className="parameter-control">
              <label>
                Domain (Optional):
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                >
                  <option value="">Auto-detect</option>
                  <option value="electrical">Electrical</option>
                  <option value="mechanical">Mechanical</option>
                  <option value="pid">P&ID</option>
                  <option value="civil">Civil</option>
                  <option value="structural">Structural</option>
                </select>
              </label>
              <span className="parameter-hint">
                Leave empty for automatic detection
              </span>
            </div>
          </div>
        </div>

        <button
          className="analyze-button"
          onClick={handleAnalyze}
          disabled={!imageFile || isAnalyzing}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="spinner" size={20} />
              <span>Analyzing... ({numCycles} cycles)</span>
            </>
          ) : (
            <>
              <Zap size={20} />
              <span>Start Flickering Analysis</span>
            </>
          )}
        </button>

        {error && <div className="error-message">❌ {error}</div>}
      </div>

      {results && (
        <div className="flickering-results">
          <div className="results-summary">
            <h3>📊 Analysis Summary</h3>
            <div className="summary-grid">
              <div className="summary-card">
                <div className="summary-label">Confidence</div>
                <div className="summary-value">
                  {(results.interpretation.confidence * 100).toFixed(1)}%
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Total Cycles</div>
                <div className="summary-value">{results.num_cycles}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Mismatches</div>
                <div className="summary-value">{results.num_mismatches}</div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Latency</div>
                <div className="summary-value">
                  {(results.system_info.total_latency_ms / 1000).toFixed(2)}s
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Memory Patterns</div>
                <div className="summary-value">
                  {results.system_info.memory_patterns}
                </div>
              </div>
              <div className="summary-card">
                <div className="summary-label">Avg Mismatch</div>
                <div className="summary-value">
                  {results.interpretation.avg_mismatch.toFixed(3)}
                </div>
              </div>
            </div>
          </div>

          <div className="interpretation-section">
            <h3>🔮 Interpretation</h3>
            <div className="interpretation-text">
              {results.interpretation.explanation}
            </div>
          </div>

          {renderAttentionTrace()}
          {renderMismatchEvents()}

          {results.alternatives && results.alternatives.length > 0 && (
            <div className="alternatives-section">
              <h3>🌳 Alternative Hypotheses</h3>
              <div className="alternatives-list">
                {results.alternatives.map((alt, idx) => (
                  <div key={idx} className="alternative-card">
                    <div className="alternative-rank">#{alt.rank}</div>
                    <div className="alternative-content">
                      <div className="alternative-type">{alt.type}</div>
                      <div className="alternative-probability">
                        <TrendingUp size={16} />
                        {(alt.probability * 100).toFixed(1)}%
                      </div>
                      <div className="alternative-rationale">
                        {alt.rationale}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
