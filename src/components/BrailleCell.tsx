import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { AppColors } from '../constants/colors';
import { BrailleCell as BrailleCellType } from '../logic/brailleLogic';

interface Props {
  cell: BrailleCellType;
  onPress?: () => void;
}

function Dot({ active }: { active: boolean }) {
  return (
    <View style={[styles.dot, active ? styles.dotActive : styles.dotInactive]} />
  );
}

export default function BrailleCell({ cell, onPress }: Props) {
  const { dots, char } = cell;

  const content = (
    <View style={styles.wrapper}>
      <View style={styles.cellBox}>
        {/* 左列: 点1,2,3 / 右列: 点4,5,6 */}
        <View style={styles.col}>
          <Dot active={!!dots[0]} />
          <Dot active={!!dots[1]} />
          <Dot active={!!dots[2]} />
        </View>
        <View style={styles.col}>
          <Dot active={!!dots[3]} />
          <Dot active={!!dots[4]} />
          <Dot active={!!dots[5]} />
        </View>
      </View>
      <Text style={styles.charLabel} numberOfLines={1}>{char}</Text>
    </View>
  );

  if (onPress) {
    return (
      <Pressable onPress={onPress} style={({ pressed }) => pressed && styles.pressed}>
        {content}
      </Pressable>
    );
  }
  return content;
}

const styles = StyleSheet.create({
  wrapper: {
    alignItems: 'center',
    marginHorizontal: 2,
  },
  cellBox: {
    flexDirection: 'row',
    gap: 2,
    backgroundColor: AppColors.SURFACE,
    borderRadius: 4,
    padding: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  col: {
    flexDirection: 'column',
    gap: 2,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotActive: {
    backgroundColor: AppColors.DOT_ACTIVE,
  },
  dotInactive: {
    backgroundColor: AppColors.DOT_INACTIVE,
  },
  charLabel: {
    fontSize: 10,
    fontWeight: 'bold',
    color: AppColors.READING_TEXT,
    textAlign: 'center',
    width: 20,
    marginTop: 2,
  },
  pressed: {
    opacity: 0.6,
  },
});
