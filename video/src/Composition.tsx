import React from "react";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  interpolate,
  Series,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import picks from "./picks.json";

type Props = {};

const FPS = 30;
const INTRO = 60;
const LAST = 100;
const TICKET = 130;
const OUTRO = 75;
const TOTAL = INTRO + LAST + TICKET * picks.tickets.length + OUTRO;

const calculateMetadata: CalculateMetadataFunction<Props> = () => {
  return {};
};

export const MyComposition = () => {
  return (
    <Composition
      id="LottoPicks"
      component={MyComponent}
      durationInFrames={TOTAL}
      fps={FPS}
      width={1080}
      height={1920}
      calculateMetadata={calculateMetadata}
    />
  );
};

const FONT = "'Helvetica Neue', Arial, sans-serif";

const Ball: React.FC<{ n: number; color: string; delay: number; size?: number }> = ({
  n,
  color,
  delay,
  size = 190,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 11, mass: 0.7 } });
  const spin = interpolate(s, [0, 1], [-200, 0]);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: `radial-gradient(circle at 32% 28%, #fff 0%, ${color} 38%, #111 120%)`,
        boxShadow: `0 0 50px ${color}88`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${s}) rotate(${spin}deg)`,
      }}
    >
      <div
        style={{
          width: size * 0.58,
          height: size * 0.58,
          borderRadius: "50%",
          background: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: FONT,
          fontWeight: 900,
          fontSize: size * 0.34,
          color: "#111",
        }}
      >
        {n}
      </div>
    </div>
  );
};

const Balls: React.FC<{ nums: number[]; color: string; start: number; size?: number }> = ({
  nums,
  color,
  start,
  size,
}) => (
  <div
    style={{
      display: "flex",
      flexWrap: "wrap",
      justifyContent: "center",
      gap: 40,
      width: 900,
    }}
  >
    {nums.map((n, i) => (
      <Ball key={n} n={n} color={color} delay={start + i * 8} size={size} />
    ))}
  </div>
);

const FadeIn: React.FC<{ delay?: number; children: React.ReactNode }> = ({ delay = 0, children }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame - delay, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return <div style={{ opacity: t, transform: `translateY(${(1 - t) * 40}px)` }}>{children}</div>;
};

const Scene: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill
    style={{
      alignItems: "center",
      justifyContent: "center",
      gap: 70,
      padding: "100px 80px",
      textAlign: "center",
      fontFamily: FONT,
      color: "#fff",
    }}
  >
    {children}
  </AbsoluteFill>
);

const Title: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({
  children,
  color = "#fff",
  size = 110,
}) => <div style={{ fontSize: size, fontWeight: 900, color, lineHeight: 1.05 }}>{children}</div>;

const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 50, color: "#c9c9e0" }}>{children}</div>
);

const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const angle = interpolate(frame, [0, TOTAL], [0, 360]);
  return (
    <AbsoluteFill
      style={{
        background: `conic-gradient(from ${angle}deg at 50% 40%, #1a0b3d, #0b1d3d, #2a0b2e, #1a0b3d)`,
      }}
    />
  );
};

export const MyComponent: React.FC<Props> = () => {
  const { lastDraw, tickets, game } = picks;
  return (
    <AbsoluteFill>
      <Background />
      <Series>
        <Series.Sequence durationInFrames={INTRO}>
          <Scene>
            <FadeIn>
              <Title size={140}>🔮 Lotto Oracle</Title>
            </FadeIn>
            <FadeIn delay={12}>
              <Sub>{game} picks for the next draw</Sub>
            </FadeIn>
          </Scene>
        </Series.Sequence>
        <Series.Sequence durationInFrames={LAST}>
          <Scene>
            <FadeIn>
              <Title size={96}>Last draw</Title>
              <Sub>{lastDraw.date}</Sub>
            </FadeIn>
            <Balls nums={lastDraw.nums} color="#9b8cff" start={10} size={170} />
            <FadeIn delay={70}>
              <Sub>Bonus: {lastDraw.bonus}</Sub>
            </FadeIn>
          </Scene>
        </Series.Sequence>
        {tickets.map((t) => (
          <Series.Sequence key={t.label} durationInFrames={TICKET}>
            <Scene>
              <FadeIn>
                <Title color={t.color}>{t.label}</Title>
                <Sub>{t.sub}</Sub>
              </FadeIn>
              <Balls nums={t.nums} color={t.color} start={15} />
            </Scene>
          </Series.Sequence>
        ))}
        <Series.Sequence durationInFrames={OUTRO}>
          <Scene>
            <FadeIn>
              <Title size={120}>Good luck! 🍀</Title>
            </FadeIn>
            <FadeIn delay={15}>
              <Sub>For entertainment only. Every draw is random.</Sub>
            </FadeIn>
          </Scene>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
