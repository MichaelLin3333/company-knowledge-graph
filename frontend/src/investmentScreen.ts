import snapshot from './investment_screen.json';
import verifiedListings from './us_listing_summary.json';

export const screenLabels: Record<string, string> = {
 anchor: 'Apple benchmark',
 retained: 'Retained for research',
 excluded: 'Excluded by price-risk screen',
 insufficient: 'Insufficient price history',
 unlisted: 'No independent public shares',
 unmapped: 'No verified own listing',
};

export type ScreenEntry = { status: string; reason: string; ticker?: string };
export type AppleScreen = {
 as_of: string;
 counts: { excluded: number; retained: number };
 companies: Record<string, ScreenEntry | undefined>;
};

export const appleInvestmentScreen: AppleScreen = snapshot;
export const appleUSListings: {
 as_of: string; count: number; retained: number; by_company: Record<string, string | undefined>;
} = verifiedListings;
export const excludedFill = '#53575d';
export const unassessedBorder = '#e5b878';
