import React, { useState } from 'react';
import {
  Modal, View, Text, Pressable, StyleSheet, ScrollView,
} from 'react-native';
import Slider from '@react-native-community/slider';
import { AppColors } from '../constants/colors';
import { AppSettings } from '../stores/historyStore';

interface Props {
  visible: boolean;
  settings: AppSettings;
  onClose: () => void;
  onUpdate: (patch: Partial<AppSettings>) => void;
}

export default function SettingsModal({ visible, settings, onClose, onUpdate }: Props) {
  const [chars, setChars]         = useState(settings.maxCharsPerLine);
  const [lines, setLines]         = useState(settings.maxLinesPerPlate);
  const [thick, setThick]         = useState(settings.plateThickness);
  const [dotHeight, setDotHeight] = useState(settings.dotHeight);

  // 親の settings が変わったら同期
  React.useEffect(() => {
    setChars(settings.maxCharsPerLine);
    setLines(settings.maxLinesPerPlate);
    setThick(settings.plateThickness);
    setDotHeight(settings.dotHeight);
  }, [settings]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={styles.dialog}>
          <Text style={styles.title}>出力設定</Text>
          <ScrollView>
            <Text style={styles.label}>1行あたりの文字数</Text>
            <View style={styles.row}>
              <Slider
                style={styles.slider}
                minimumValue={5} maximumValue={30} step={1}
                value={chars}
                minimumTrackTintColor={AppColors.PRIMARY}
                onValueChange={(v) => setChars(Math.round(v))}
                onSlidingComplete={(v) => onUpdate({ maxCharsPerLine: Math.round(v) })}
              />
              <Text style={styles.valueLabel}>{chars}文字</Text>
            </View>

            <Text style={styles.label}>1プレートあたりの行数</Text>
            <View style={styles.row}>
              <Slider
                style={styles.slider}
                minimumValue={1} maximumValue={10} step={1}
                value={lines}
                minimumTrackTintColor={AppColors.PRIMARY}
                onValueChange={(v) => setLines(Math.round(v))}
                onSlidingComplete={(v) => onUpdate({ maxLinesPerPlate: Math.round(v) })}
              />
              <Text style={styles.valueLabel}>{lines}行</Text>
            </View>

            <Text style={styles.label}>プレートの厚さ (mm)</Text>
            <View style={styles.row}>
              <Slider
                style={styles.slider}
                minimumValue={0.5} maximumValue={2.0} step={0.1}
                value={thick}
                minimumTrackTintColor={AppColors.PRIMARY}
                onValueChange={(v) => setThick(Math.round(v * 10) / 10)}
                onSlidingComplete={(v) => onUpdate({ plateThickness: Math.round(v * 10) / 10 })}
              />
              <Text style={styles.valueLabel}>{thick.toFixed(1)}mm</Text>
            </View>

            <Text style={styles.label}>ドットの高さ (mm)</Text>
            <View style={styles.row}>
              <Slider
                style={styles.slider}
                minimumValue={0.2} maximumValue={1.0} step={0.05}
                value={dotHeight}
                minimumTrackTintColor={AppColors.PRIMARY}
                onValueChange={(v) => setDotHeight(Math.round(v * 20) / 20)}
                onSlidingComplete={(v) => onUpdate({ dotHeight: Math.round(v * 20) / 20 })}
              />
              <Text style={styles.valueLabel}>{dotHeight.toFixed(2)}mm</Text>
            </View>

            <Text style={styles.label}>点字言語 / Braille Language</Text>
            <View style={styles.segmentedControl}>
              <Pressable
                style={[styles.segment, settings.brailleLanguage === 'en' && styles.segmentActive]}
                onPress={() => onUpdate({ brailleLanguage: 'en' })}
              >
                <Text style={[styles.segmentText, settings.brailleLanguage === 'en' && styles.segmentTextActive]}>
                  English
                </Text>
              </Pressable>
              <Pressable
                style={[styles.segment, settings.brailleLanguage === 'ja' && styles.segmentActive]}
                onPress={() => onUpdate({ brailleLanguage: 'ja' })}
              >
                <Text style={[styles.segmentText, settings.brailleLanguage === 'ja' && styles.segmentTextActive]}>
                  日本語
                </Text>
              </Pressable>
            </View>
          </ScrollView>

          <View style={styles.actions}>
            <Pressable onPress={onClose} style={styles.actionBtn}>
              <Text style={styles.actionText}>閉じる</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  dialog: {
    width: '85%',
    backgroundColor: AppColors.SURFACE,
    borderRadius: 14,
    padding: 20,
    maxHeight: '70%',
  },
  title: {
    fontSize: 17,
    fontWeight: '600',
    color: AppColors.TEXT_MAIN,
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    color: AppColors.TEXT_SUB,
    marginTop: 12,
    marginBottom: 4,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  slider: {
    flex: 1,
  },
  valueLabel: {
    width: 56,
    fontSize: 13,
    color: AppColors.TEXT_MAIN,
    textAlign: 'right',
  },
  segmentedControl: {
    flexDirection: 'row',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: AppColors.PRIMARY,
    overflow: 'hidden',
    marginTop: 4,
  },
  segment: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  segmentActive: {
    backgroundColor: AppColors.PRIMARY,
  },
  segmentText: {
    fontSize: 14,
    color: AppColors.PRIMARY,
  },
  segmentTextActive: {
    color: AppColors.SURFACE,
    fontWeight: '600',
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 16,
  },
  actionBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  actionText: {
    fontSize: 16,
    color: AppColors.PRIMARY,
    fontWeight: '500',
  },
});
