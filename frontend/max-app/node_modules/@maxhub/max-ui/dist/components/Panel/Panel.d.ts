import { type ComponentProps } from 'react';
export type PanelMode = 'primary' | 'secondary';
export interface PanelProps extends ComponentProps<'div'> {
    mode?: PanelMode;
    centeredX?: boolean;
    centeredY?: boolean;
}
export declare const Panel: import("react").ForwardRefExoticComponent<Omit<PanelProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=Panel.d.ts.map