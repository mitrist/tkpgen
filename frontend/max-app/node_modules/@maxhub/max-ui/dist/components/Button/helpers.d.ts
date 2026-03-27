import { type ReactNode } from 'react';
import { type CounterProps } from '../Counter';
import { type SpinnerAppearance } from '../Spinner';
import { type ButtonAppearance, type ButtonMode, type ButtonSize } from './Button';
export declare const getButtonSpinnerSize: (buttonSize: ButtonSize) => number;
export declare const getButtonSpinnerAppearance: (buttonAppearance: ButtonAppearance, buttonMode: ButtonMode) => SpinnerAppearance;
export declare const getButtonCounterAppearance: (buttonAppearance: ButtonAppearance, buttonMode: ButtonMode) => Pick<CounterProps, "appearance" | "mode">;
export declare const injectButtonIndicator: (indicatorNode: ReactNode, buttonAppearance: ButtonAppearance, buttonMode: ButtonMode, disabled?: boolean) => ReactNode;
//# sourceMappingURL=helpers.d.ts.map