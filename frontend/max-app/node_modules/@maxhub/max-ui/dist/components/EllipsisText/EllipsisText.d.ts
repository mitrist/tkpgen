import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../types';
export interface EllipsisTextProps extends ComponentProps<'div'>, AsChildProp {
    /**
     * Максимальное количество видимых строк
     *
     * FYI: при `maxLines > 1` используется свойство line-clamp, которое поддерживается не всеми версиями браузеров
     *
     * https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-line-clamp
     */
    maxLines?: number;
}
export declare const EllipsisText: import("react").ForwardRefExoticComponent<Omit<EllipsisTextProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=EllipsisText.d.ts.map