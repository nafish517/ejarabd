const EN_TO_BN_NUM: Record<string, string> = {
  '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
  '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
};

export function toBnNumber(val: string | number): string {
  return String(val).replace(/[0-9]/g, (digit) => EN_TO_BN_NUM[digit] || digit);
}

export function formatBDT(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) {
    return 'নোটিশে প্রাক্কলিত মূল্য উল্লেখ নেই (দলিল দেখতে হবে)';
  }

  if (amount >= 10_000_000) {
    const crore = (amount / 10_000_000).toFixed(2).replace(/\.?0+$/, '');
    return `৳ ${toBnNumber(crore)} কোটি`;
  } else if (amount >= 100_000) {
    const lakh = (amount / 100_000).toFixed(2).replace(/\.?0+$/, '');
    return `৳ ${toBnNumber(lakh)} লাখ`;
  } else {
    return `৳ ${toBnNumber(amount.toLocaleString('en-IN'))}`;
  }
}

export function formatSecurityBDT(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) {
    return 'নোটিশে উল্লিখিত নয়';
  }
  if (amount >= 100_000) {
    const lakh = (amount / 100_000).toFixed(2).replace(/\.?0+$/, '');
    return `৳ ${toBnNumber(lakh)} লাখ`;
  }
  return `৳ ${toBnNumber(amount.toLocaleString('en-IN'))}`;
}

export function formatBSTDate(isoDate: string | null | undefined): string {
  if (!isoDate) return 'নোটিশে তারিখ পাওয়া যায়নি';

  try {
    const dt = new Date(isoDate);
    const monthsBn = [
      'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
      'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর'
    ];

    const day = toBnNumber(dt.getDate());
    const month = monthsBn[dt.getMonth()];
    const year = toBnNumber(dt.getFullYear());

    const hours = dt.getHours();
    const minutes = toBnNumber(String(dt.getMinutes()).padStart(2, '0'));
    const period = hours < 12 ? 'সকাল' : hours < 15 ? 'দুপুর' : hours < 18 ? 'বিকাল' : 'সন্ধ্যা';
    const displayHour = toBnNumber(hours % 12 || 12);

    return `${day} ${month} ${year}, ${period} ${displayHour}:${minutes} মিনিট (BST)`;
  } catch {
    return isoDate;
  }
}

export function getRemainingDaysBadge(isoDate: string): { text: string; isUrgent: boolean; isPassed: boolean } {
  try {
    const target = new Date(isoDate).getTime();
    const now = new Date('2026-09-21T15:50:00+06:00').getTime(); // বর্তমান সিমুলেটেড সময়
    const diffMs = target - now;

    if (diffMs <= 0) {
      return { text: 'সময় উত্তীর্ণ', isUrgent: true, isPassed: true };
    }

    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) {
      return { text: 'আজই শেষ দিন!', isUrgent: true, isPassed: false };
    } else if (diffDays <= 3) {
      return { text: `${toBnNumber(diffDays)} দিন বাকি (জরুরি)`, isUrgent: true, isPassed: false };
    } else {
      return { text: `${toBnNumber(diffDays)} দিন বাকি`, isUrgent: false, isPassed: false };
    }
  } catch {
    return { text: 'তারিখ যাচাই করুন', isUrgent: false, isPassed: false };
  }
}
