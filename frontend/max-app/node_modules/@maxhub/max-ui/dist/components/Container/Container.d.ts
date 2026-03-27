import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../types';
export interface ContainerProps extends ComponentProps<'div'>, AsChildProp {
    fullWidth?: boolean;
}
export declare const Container: import("react").ForwardRefExoticComponent<Omit<ContainerProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=Container.d.ts.map