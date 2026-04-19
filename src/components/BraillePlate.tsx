import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { AppColors } from '../constants/colors';
import BrailleCell from './BrailleCell';
import { BrailleCell as BrailleCellType } from '../logic/brailleLogic';

export interface FlatCellInfo extends BrailleCellType {
  wordIdx: number;  // -1 = スペース（単語間）
  orig: string;
  isNewLine?: boolean; // 強制改行マーカー（段落区切り）
}

interface Props {
  plateIndex: number;
  lines: FlatCellInfo[][];
  onCellPress: (wordIdx: number) => void;
}

export default function BraillePlate({ plateIndex, lines, onCellPress }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.plateLabel}>Plate #{plateIndex + 1}</Text>
      <View style={styles.plateBody}>
        {lines.map((lineCells, lineIdx) => (
          <ScrollView
            key={lineIdx}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.lineRow}
          >
            {lineCells.map((cell, cellIdx) => (
              <BrailleCell
                key={cellIdx}
                cell={cell}
                onPress={cell.wordIdx !== -1 ? () => onCellPress(cell.wordIdx) : undefined}
              />
            ))}
          </ScrollView>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 8,
  },
  plateLabel: {
    fontSize: 14,
    fontWeight: 'bold',
    color: AppColors.PRIMARY,
    marginBottom: 4,
  },
  plateBody: {
    backgroundColor: 'rgba(255,255,255,0.54)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(0,0,0,0.12)',
    padding: 10,
    gap: 10,
  },
  lineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
  },
});
