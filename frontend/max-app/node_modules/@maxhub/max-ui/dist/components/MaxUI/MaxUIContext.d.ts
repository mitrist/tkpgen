import { type ColorSchemeType, type PlatformType } from '../../types';
export interface MaxUIContextInterface {
    platform: PlatformType;
    colorScheme: ColorSchemeType;
}
export declare const MaxUIContext: import("react").Context<MaxUIContextInterface>;
export declare const useAppearance: () => MaxUIContextInterface;
//# sourceMappingURL=MaxUIContext.d.ts.map