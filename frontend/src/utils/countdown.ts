/**
 * Live Asia/Dhaka (BST = UTC+6) Countdown & Stopwatch Utility
 * 
 * Calculates exact real-time seconds, minutes, and hours remaining
 * until the next scheduled notification dispatch slot.
 */

export interface DispatchCountdown {
  formatted: string;
  hours: number;
  minutes: number;
  seconds: number;
  targetSlot: string;
  targetSlot12h: string;
  isToday: boolean;
  dayLabel: string;
  totalSeconds: number;
  isDispatchingNow: boolean;
}

export function getNextDispatchCountdown(schedules: string[]): DispatchCountdown {
  if (!schedules || schedules.length === 0) {
    return {
      formatted: 'কোনো স্লট নেই',
      hours: 0,
      minutes: 0,
      seconds: 0,
      targetSlot: 'None',
      targetSlot12h: 'কোনো শিডিউল স্লট নির্ধারণ করা হয়নি',
      isToday: false,
      dayLabel: '',
      totalSeconds: 0,
      isDispatchingNow: false,
    };
  }

  // Calculate current Bangladesh Standard Time (BST = UTC+6)
  const now = new Date();
  const utcMs = now.getTime() + now.getTimezoneOffset() * 60000;
  const bstNow = new Date(utcMs + 6 * 3600000);

  // Normalize and parse slots
  const validSlots: { hour: number; minute: number; raw: string }[] = [];
  for (const s of schedules) {
    const parts = s.trim().split(':');
    if (parts.length === 2) {
      const h = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10);
      if (!isNaN(h) && !isNaN(m) && h >= 0 && h < 24 && m >= 0 && m < 60) {
        validSlots.push({
          hour: h,
          minute: m,
          raw: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
        });
      }
    }
  }

  if (validSlots.length === 0) {
    return {
      formatted: 'স্লট সঠিক নয়',
      hours: 0,
      minutes: 0,
      seconds: 0,
      targetSlot: 'Invalid',
      targetSlot12h: 'অবৈধ স্লট',
      isToday: false,
      dayLabel: '',
      totalSeconds: 0,
      isDispatchingNow: false,
    };
  }

  // Sort slots chronologically
  validSlots.sort((a, b) => a.hour * 60 + a.minute - (b.hour * 60 + b.minute));

  // Current time in seconds within the day
  const currentSecondsInDay =
    bstNow.getHours() * 3600 + bstNow.getMinutes() * 60 + bstNow.getSeconds();
  const currentMinutesInDay = bstNow.getHours() * 60 + bstNow.getMinutes();

  // Find next upcoming slot today
  let targetSlot = validSlots.find(
    (slot) => slot.hour * 60 + slot.minute > currentMinutesInDay
  );
  let isToday = true;

  if (!targetSlot) {
    // All slots for today have completed or passed; wrap to tomorrow's first slot
    targetSlot = validSlots[0];
    isToday = false;
  }

  const targetSecondsInDay = targetSlot.hour * 3600 + targetSlot.minute * 60;
  let diffSec = targetSecondsInDay - currentSecondsInDay;
  if (!isToday) {
    diffSec += 24 * 3600;
  }

  if (diffSec < 0) diffSec = 0;

  const isDispatchingNow = diffSec === 0;

  const hours = Math.floor(diffSec / 3600);
  const minutes = Math.floor((diffSec % 3600) / 60);
  const seconds = diffSec % 60;

  let formatted = '';
  if (isDispatchingNow) {
    formatted = 'ডিসপ্যাচ হচ্ছে...';
  } else if (hours > 0) {
    formatted = `${String(hours).padStart(2, '0')}h : ${String(minutes).padStart(2, '0')}m : ${String(seconds).padStart(2, '0')}s`;
  } else {
    formatted = `${String(minutes).padStart(2, '0')}m : ${String(seconds).padStart(2, '0')}s`;
  }

  // 12-hour format label
  const period = targetSlot.hour >= 12 ? 'PM' : 'AM';
  const h12 = targetSlot.hour % 12 === 0 ? 12 : targetSlot.hour % 12;
  const banglaPeriod =
    targetSlot.hour < 6
      ? 'রাত'
      : targetSlot.hour < 12
      ? 'সকাল'
      : targetSlot.hour < 15
      ? 'দুপুর'
      : targetSlot.hour < 18
      ? 'বিকাল'
      : targetSlot.hour < 20
      ? 'সন্ধ্যা'
      : 'রাত';
  const targetSlot12h = `${banglaPeriod} ${h12}:${String(targetSlot.minute).padStart(2, '0')} ${period}`;

  return {
    formatted,
    hours,
    minutes,
    seconds,
    targetSlot: targetSlot.raw,
    targetSlot12h,
    isToday,
    dayLabel: isToday ? 'আজকে' : 'আগামীকাল',
    totalSeconds: diffSec,
    isDispatchingNow,
  };
}
